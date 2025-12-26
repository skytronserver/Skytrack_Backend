#!/usr/bin/env bash
set -euo pipefail

# Configurable settings
GEOSERVER_URL=${GEOSERVER_URL:-"http://localhost:8080/geoserver"}
ADMIN_USER=${ADMIN_USER:-"admin"}
ADMIN_PASS=${ADMIN_PASS:-"geoserver"}
WORKSPACE=${WORKSPACE:-"skytron"}
LAYERGROUP_NAME=${LAYERGROUP_NAME:-"Silchar_map_soi"}

PG_HOST=${PG_HOST:-"135.235.166.209"}
PG_PORT=${PG_PORT:-"5432"}
PG_DB=${PG_DB:-"soi_silchar"}
PG_SCHEMA=${PG_SCHEMA:-"soi"}
PG_USER=${PG_USER:-"geoserver"}
PG_PASS=${PG_PASS:-"StrongPass_123"}

command -v curl >/dev/null || { echo "curl not found"; exit 1; }
command -v psql >/dev/null || { echo "psql not found"; exit 1; }
command -v bc >/dev/null || echo "bc not found; bounds expansion will be approximate."
command -v awk >/dev/null || { echo "awk not found"; exit 1; }

# Ensure workspace exists (but do not fail if it does)
WS_CODE=$(curl -s -o /tmp/ws_get.out -w "%{http_code}\n" -u "${ADMIN_USER}:${ADMIN_PASS}" "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}")
if [[ "$WS_CODE" != "200" ]]; then
  echo "Workspace ${WORKSPACE} not found via GET (HTTP $WS_CODE). Attempting create..."
  curl -s -o /tmp/ws_create.out -u "${ADMIN_USER}:${ADMIN_PASS}" -H "Content-Type: application/json" \
    -X POST "${GEOSERVER_URL}/rest/workspaces" -d "{\"workspace\":{\"name\":\"${WORKSPACE}\"}}" >/dev/null || true
fi

# Get list of tables and geometry types from PostGIS
export PGPASSWORD="${PG_PASS}"
readarray -t LAYER_ROWS < <(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -tAc \
  "SELECT f_table_name, type FROM geometry_columns WHERE f_table_schema='${PG_SCHEMA}' ORDER BY 1;")

if [[ ${#LAYER_ROWS[@]} -eq 0 ]]; then
  echo "No geometry_columns rows found; falling back to information_schema and probing types."
  readarray -t TBL_LIST < <(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -tAc \
    "SELECT table_name FROM information_schema.tables WHERE table_schema='${PG_SCHEMA}' ORDER BY 1;")
  LAYER_ROWS=()
  for tbl in "${TBL_LIST[@]}"; do
    [[ -z "$tbl" ]] && continue
    # Try to detect geometry type from 'geom' column
    gtype=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -tAc \
      "SELECT DISTINCT ST_GeometryType(geom) FROM \"${PG_SCHEMA}\".\"${tbl}\" WHERE geom IS NOT NULL LIMIT 1;" || true)
    gtype=${gtype:-"GEOMETRY"}
    # Normalize 'ST_' prefix if present
    gtype=${gtype#ST_}
    LAYER_ROWS+=("${tbl}|${gtype}")
  done
fi

# Get list of published layer names in the workspace via REST and intersect
REST_LAYERS_RAW=$(curl -s -u "${ADMIN_USER}:${ADMIN_PASS}" "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/layers.json" || true)
readarray -t REST_LAYER_NAMES < <(echo "$REST_LAYERS_RAW" | grep -o '"name":"[^"]\+"' | awk -F'"' '{print $4}')

is_published() {
  local name="$1"
  for rl in "${REST_LAYER_NAMES[@]}"; do
    [[ "$rl" == "$name" ]] && return 0
  done
  return 1
}

# Separate layers by geometry for ordering and styles
POLYGON_LAYERS=()
LINE_LAYERS=()
POINT_LAYERS=()
ALL_LAYERS=()
ALL_STYLES=()

minx=""
miny=""
maxx=""
maxy=""

for row in "${LAYER_ROWS[@]}"; do
  [[ -z "$row" ]] && continue
  tbl=${row%%|*}
  gtype=${row#*|}
  # Only include layers that are published in GeoServer
  if ! is_published "$tbl"; then
    continue
  fi
  # Strip MULTI prefix for style mapping
  base_type=${gtype#MULTI}
  case "$base_type" in
    POLYGON|CURVEPOLYGON)
      POLYGON_LAYERS+=("${tbl}")
      ;;
    LINESTRING|MULTICURVE|COMPOUNDCURVE)
      LINE_LAYERS+=("${tbl}")
      ;;
    POINT)
      POINT_LAYERS+=("${tbl}")
      ;;
    *)
      # Default to polygon for areas; else line/point heuristics
      POLYGON_LAYERS+=("${tbl}")
      ;;
  esac
  # Compute extent and update group bounds
  bbox=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -tAc \
    "SELECT ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext) FROM (SELECT ST_Extent(geom) ext FROM \"${PG_SCHEMA}\".\"${tbl}\") s;" || true)
  # bbox may be empty if table has no geometries
  if [[ -n "$bbox" ]]; then
    x1=$(echo "$bbox" | awk -F '|' '{print $1}')
    y1=$(echo "$bbox" | awk -F '|' '{print $2}')
    x2=$(echo "$bbox" | awk -F '|' '{print $3}')
    y2=$(echo "$bbox" | awk -F '|' '{print $4}')
    # Initialize or expand (float-safe if bc is available)
    if [[ -z "$minx" ]]; then
      minx=$x1; miny=$y1; maxx=$x2; maxy=$y2
    else
      if command -v bc >/dev/null; then
        (( $(echo "$x1 < $minx" | bc -l) )) && minx=$x1 || true
        (( $(echo "$y1 < $miny" | bc -l) )) && miny=$y1 || true
        (( $(echo "$x2 > $maxx" | bc -l) )) && maxx=$x2 || true
        (( $(echo "$y2 > $maxy" | bc -l) )) && maxy=$y2 || true
      fi
    fi
  fi

done

# Build ordered layer list: polygons, lines, points
ORDERED_LAYERS=("${POLYGON_LAYERS[@]}" "${LINE_LAYERS[@]}" "${POINT_LAYERS[@]}")

# Collect ordered layer names
for tbl in "${ORDERED_LAYERS[@]}"; do
  ALL_LAYERS+=("${tbl}")
done

# Fallback bounds if none computed
minx=${minx:-"-180"}
miny=${miny:-"-90"}
maxx=${maxx:-"180"}
maxy=${maxy:-"90"}

# Create JSON arrays
if [[ ${#ALL_LAYERS[@]} -eq 0 ]]; then
  echo "No published layers found to include in the layer group."
  exit 1
fi
layers_json=$(printf '"%s"\n' "${ALL_LAYERS[@]}" | paste -sd, -)
styles_json=""

# Create the layer group
cat > /tmp/lg_payload.json <<JSON
{
  "layerGroup": {
    "name": "${LAYERGROUP_NAME}",
    "workspace": "${WORKSPACE}",
    "mode": "SINGLE",
    "layers": { "layer": [ ${layers_json} ] },
  
    "bounds": {
      "minx": ${minx},
      "miny": ${miny},
      "maxx": ${maxx},
      "maxy": ${maxy},
      "crs": "EPSG:4326"
    }
  }
}
JSON

LG_CODE=$(curl -s -o /tmp/layergroup.out -w "%{http_code}\n" -u "${ADMIN_USER}:${ADMIN_PASS}" -H "Content-Type: application/json" \
  -X POST "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/layergroups" -d @/tmp/lg_payload.json)

if [[ "$LG_CODE" == "409" ]]; then
  echo "Layer group ${LAYERGROUP_NAME} already exists; updating..."
  LG_CODE=$(curl -s -o /tmp/layergroup.out -w "%{http_code}\n" -u "${ADMIN_USER}:${ADMIN_PASS}" -H "Content-Type: application/json" \
    -X PUT "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/layergroups/${LAYERGROUP_NAME}" -d @/tmp/lg_payload.json)
fi

if [[ "$LG_CODE" != "201" && "$LG_CODE" != "200" ]]; then
  echo "LayerGroup create/update returned HTTP $LG_CODE"
  cat /tmp/layergroup.out
  exit 1
fi

echo "Layer group '${LAYERGROUP_NAME}' created/updated in workspace '${WORKSPACE}'."