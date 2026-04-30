#!/usr/bin/env bash
set -euo pipefail

# Configurable settings
GEOSERVER_URL=${GEOSERVER_URL:-"http://localhost:8080/geoserver"}
ADMIN_USER=${ADMIN_USER:-"admin"}
ADMIN_PASS=${ADMIN_PASS:-"geoserver"}

# GeoServer workspace to publish into (independent of DB schema)
WORKSPACE=${WORKSPACE:-"skytron"}
SKIP_FEATURE_TYPES=${SKIP_FEATURE_TYPES:-"false"}

PG_HOST=${PG_HOST:-""}
PG_PORT=${PG_PORT:-"5432"}
PG_DB=${PG_DB:-"soi_silchar"}
PG_SCHEMA=${PG_SCHEMA:-"soi"}
PG_USER=${PG_USER:-"geoserver"}
PG_PASS=${PG_PASS:-"StrongPass_123"}

# Ensure required tools are present
command -v curl >/dev/null || { echo "curl not found"; exit 1; }
command -v psql >/dev/null || { echo "psql not found"; exit 1; }

# Create workspace (idempotent)
echo "Creating GeoServer workspace '${WORKSPACE}' (if missing)..."
WS_CODE=$(curl -s -o /tmp/ws_create.out -w "%{http_code}\n" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -X POST "${GEOSERVER_URL}/rest/workspaces" \
  -d "{\"workspace\":{\"name\":\"${WORKSPACE}\"}}")
if [[ "$WS_CODE" != "201" && "$WS_CODE" != "409" ]]; then
  echo "Workspace create returned HTTP $WS_CODE"
  cat /tmp/ws_create.out
  exit 1
fi

# Create PostGIS datastore (idempotent)
echo "Ensuring PostGIS datastore 'soi_silchar_pg' exists in workspace '${WORKSPACE}'..."
EXIST_CODE=$(curl -s -o /tmp/ds_exists.out -w "%{http_code}\n" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Accept: application/json" \
  "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/datastores/soi_silchar_pg")
if [[ "$EXIST_CODE" == "200" ]]; then
  echo "Datastore already exists. Skipping creation."
else
  echo "Creating PostGIS datastore 'soi_silchar_pg' in workspace '${WORKSPACE}'..."
DATASTORE_JSON=$(cat <<JSON
{
  "dataStore": {
    "name": "soi_silchar_pg",
    "type": "PostGIS",
    "enabled": true,
    "connectionParameters": {
      "database": "${PG_DB}",
      "host": "${PG_HOST}",
      "port": "${PG_PORT}",
      "user": "${PG_USER}",
      "passwd": "${PG_PASS}",
      "schema": "${PG_SCHEMA}",
      "dbtype": "postgis"
    }
  }
}
JSON
)

  DS_CODE=$(curl -s -o /tmp/ds_create.out -w "%{http_code}\n" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -X POST "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/datastores" \
    -d "${DATASTORE_JSON}")
  if [[ "$DS_CODE" != "201" && "$DS_CODE" != "409" ]]; then
    echo "Datastore create returned HTTP $DS_CODE"
    cat /tmp/ds_create.out
    # If creation failed, but a subsequent GET says it exists, continue
    EXIST_CODE2=$(curl -s -o /tmp/ds_exists2.out -w "%{http_code}\n" \
      -u "${ADMIN_USER}:${ADMIN_PASS}" \
      -H "Accept: application/json" \
      "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/datastores/soi_silchar_pg")
    if [[ "$EXIST_CODE2" != "200" ]]; then
      exit 1
    fi
    echo "Datastore appears to exist; continuing."
  fi
fi

# Get list of tables in the schema
export PGPASSWORD="${PG_PASS}"
TABLES=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -tAc "SELECT table_name FROM information_schema.tables WHERE table_schema='${PG_SCHEMA}' ORDER BY 1;")

# Publish each table as a feature type (unless skipped)
if [[ "$SKIP_FEATURE_TYPES" != "true" ]]; then
  for tbl in ${TABLES}; do
    [[ -z "$tbl" ]] && continue
    echo "Publishing layer: $tbl"
  FEATURETYPE_JSON=$(cat <<JSON
{
  "featureType": {
    "name": "${tbl}",
    "nativeName": "${tbl}",
    "title": "${tbl}",
    "srs": "EPSG:4326"
  }
}
JSON
)

  FT_CODE=$(curl -s -o /tmp/ft_${tbl}.out -w "%{http_code}\n" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -X POST "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/datastores/soi_silchar_pg/featuretypes" \
    -d "${FEATURETYPE_JSON}")
    if [[ "$FT_CODE" != "201" && "$FT_CODE" != "409" ]]; then
      echo "FeatureType $tbl returned HTTP $FT_CODE"
      cat /tmp/ft_${tbl}.out
      exit 1
    fi
  done
else
  echo "Skipping feature type publishing as requested (SKIP_FEATURE_TYPES=true)."
fi

echo "All feature types processed. Creating layer group 'Silchar_map_soi' in workspace '${WORKSPACE}'..."

# Build workspace-qualified layer list
TMP_LAYERS_LIST=/tmp/soi_layers_list.txt
: > "$TMP_LAYERS_LIST"
for tbl in ${TABLES}; do
  [[ -z "$tbl" ]] && continue
  echo "\"${WORKSPACE}:${tbl}\"" >> "$TMP_LAYERS_LIST"
done
LAYERS_CSV=$(paste -sd, "$TMP_LAYERS_LIST")

# Create layer group with EPSG:4326 world bounds
LAYERGROUP_JSON=$(cat <<JSON
{
  "layerGroup": {
    "name": "Silchar_map_soi",
    "mode": "SINGLE",
    "workspace": "${WORKSPACE}",
    "layers": { "layer": [ ${LAYERS_CSV} ] },
    "bounds": {
      "minx": -180.0,
      "miny": -90.0,
      "maxx": 180.0,
      "maxy": 90.0,
      "crs": "EPSG:4326"
    }
  }
}
JSON
)

LG_CODE=$(curl -s -o /tmp/layergroup.out -w "%{http_code}\n" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -X POST "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/layergroups" \
  -d "${LAYERGROUP_JSON}")
if [[ "$LG_CODE" != "201" && "$LG_CODE" != "409" ]]; then
  echo "LayerGroup create returned HTTP $LG_CODE"
  cat /tmp/layergroup.out
  exit 1
fi

echo "Publishing complete. Layer group 'Silchar_map_soi' is available under workspace '${WORKSPACE}'."
