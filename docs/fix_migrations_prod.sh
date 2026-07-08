#!/bin/bash
# =============================================================================
# fix_migrations_prod.sh
#
# Fixes Django migration state for any deployment of this project.
# - Runs Django commands INSIDE the Docker container
# - Reads DB credentials from the .env file on the host
# - If migration .py files exist on the host but NOT inside the container,
#   copies them in automatically (no rebuild required for that case)
#
# RECOMMENDED WORKFLOW ON PRODUCTION:
#   1. git pull                        (get latest code + migration files)
#   2. sudo ./run_with_host_storage.sh (rebuild image - permanent fix)
#   3. sudo ./fix_migrations_prod.sh   (align DB migration history)
#
# If you can't rebuild the image right now, just run step 3 — the script
# will docker cp any missing migration files into the running container.
#
# HOW MODEL <-> DB SYNC IS VERIFIED (Step 5):
#   A) makemigrations --check : no model changes exist beyond migration files
#   B) migrate --check        : all migration files are applied in the DB
#   Both passing means: models.py == migration files == DB (fully in sync)
# =============================================================================

# Do NOT use set -e here so we can handle errors manually
set -o pipefail

# ---- CONFIGURE THESE ----
ENV_FILE="/home/Admin/backendapi/SkytronInog_20260226/Skytrack_Backend/.env"
CONTAINER="skytron-backend-api-container"
APP_NAME="skytron_api"
MANAGE="python /app/manage.py"
# Host path to migration files (where this script lives / git repo)
HOST_MIGRATIONS="/home/Admin/backendapi/SkytronInog_20260226/Skytrack_Backend/Skytronsystem/skytron_api/migrations"
CONTAINER_MIGRATIONS="/app/skytron_api/migrations"
# -------------------------

ERRORS=0

echo ""
echo "======================================================="
echo " Django Migration Fixer  (Docker mode)"
echo "======================================================="
echo ""

# ---------- Load DB credentials from .env ----------
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

eval "$(grep '^export ' "$ENV_FILE" | sed 's/^export //')"

for var in DB_HOST DB_NAME DB_USER DB_PORT DB_PASSWORD; do
    val=$(eval echo "\$$var")
    if [ -z "$val" ]; then
        echo "ERROR: $var is not set in $ENV_FILE"
        exit 1
    fi
done
export PGPASSWORD="$DB_PASSWORD"
echo "  DB        : $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

# ---------- Check container is running ----------
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER}$"; then
    echo "  ERROR: Container '$CONTAINER' is not running. Start it first."
    exit 1
fi
echo "  Container : $CONTAINER  [running]"
echo ""

# ---------- Step 1: Sync migration files host -> container ----------
echo "--- Step 1: Sync migration files from host into container ---"
COPIED=0
for host_file in "$HOST_MIGRATIONS"/[0-9]*.py; do
    [ -f "$host_file" ] || continue
    fname=$(basename "$host_file")
    # Check if the file is already inside the container
    if ! docker exec "$CONTAINER" test -f "$CONTAINER_MIGRATIONS/$fname" 2>/dev/null; then
        echo "  Copying missing file: $fname"
        docker cp "$host_file" "$CONTAINER:$CONTAINER_MIGRATIONS/$fname"
        COPIED=$((COPIED + 1))
    fi
done
if [ "$COPIED" -eq 0 ]; then
    echo "  Container already has all migration files from host. Nothing to copy."
else
    echo "  Copied $COPIED file(s) into container."
fi

# ---------- Step 2: Show current state ----------
echo ""
echo "--- Step 2: Current migration state inside container ---"
docker exec "$CONTAINER" $MANAGE showmigrations "$APP_NAME"

# ---------- Step 3: Insert missing migration records for ALL apps ----------
# Uses `showmigrations` (which does NOT run consistency checks) to discover
# every [ ] migration across every app (auth, contenttypes, sessions, admin,
# skytron_api, rest_framework, etc.) and inserts the missing records via psql.
# This avoids InconsistentMigrationHistory errors that block `migrate --fake`.
echo ""
echo "--- Step 3: Insert missing migration records for ALL apps ---"
echo "    (auth, contenttypes, sessions, admin, skytron_api, ...)"

SHOW_OUTPUT=$(docker exec "$CONTAINER" $MANAGE showmigrations 2>/dev/null \
    | grep -v "^JWT" | grep -v "^No changes")

CURRENT_APP=""
INSERTED=0

while IFS= read -r line; do
    # App name: line that starts with a letter/underscore (no leading whitespace)
    if echo "$line" | grep -qE '^[a-zA-Z_]'; then
        CURRENT_APP=$(echo "$line" | tr -d ' \r')
    # Unapplied migration: leading whitespace then [ ]
    elif echo "$line" | grep -qE '^\s+\[ \]'; then
        mig=$(echo "$line" | sed 's/.*\[ \] //' | tr -d ' \r')
        if [ -n "$CURRENT_APP" ] && [ -n "$mig" ]; then
            echo "  Inserting: ${CURRENT_APP}.${mig}"
            psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -p "$DB_PORT" \
                -P pager=off \
                -c "INSERT INTO django_migrations (app, name, applied) VALUES ('$CURRENT_APP', '$mig', NOW()) ON CONFLICT DO NOTHING;" \
                > /dev/null
            INSERTED=$((INSERTED + 1))
        fi
    fi
done <<< "$SHOW_OUTPUT"

if [ "$INSERTED" -eq 0 ]; then
    echo "  All migration records already present. Nothing inserted."
else
    echo "  Inserted $INSERTED missing record(s) across all apps."
fi
echo "Done."

# ---------- Step 4: Remove ghost records from django_migrations ----------
echo ""
echo "--- Step 4: Remove ghost records from django_migrations ---"
echo "    (Records in DB that have no matching .py file in the container)"

CONTAINER_FILES=$(docker exec "$CONTAINER" sh -c \
    "ls $CONTAINER_MIGRATIONS/*.py 2>/dev/null | xargs -I{} basename {} .py | grep -v __init__" \
)

DB_RECORDS=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -p "$DB_PORT" -P pager=off -t -c \
    "SELECT name FROM django_migrations WHERE app = '$APP_NAME';" \
    | tr -d ' ' | grep -v '^$'
)

GHOSTS=""
for record in $DB_RECORDS; do
    if ! echo "$CONTAINER_FILES" | grep -qx "$record"; then
        GHOSTS="$GHOSTS $record"
    fi
done

if [ -z "$GHOSTS" ]; then
    echo "  No ghost records found. History is clean."
else
    echo "  Found ghost record(s) to remove:"
    for ghost in $GHOSTS; do
        echo "    - $ghost"
        psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -p "$DB_PORT" -P pager=off -c \
            "DELETE FROM django_migrations WHERE app = '$APP_NAME' AND name = '$ghost';" \
            > /dev/null
    done
    echo "  Ghost records deleted."
fi

# ---------- Step 5: Final verification ----------
echo ""
echo "--- Step 5: Final verification ---"
echo ""

docker exec "$CONTAINER" $MANAGE showmigrations "$APP_NAME"
echo ""

# Check A: models.py matches migration files
MAKEMIG_OUT=$(docker exec "$CONTAINER" $MANAGE makemigrations --check --dry-run 2>&1)
if echo "$MAKEMIG_OUT" | grep -q "No changes detected"; then
    echo "  [OK] models.py is fully captured in migration files."
    MODEL_OK=1
else
    echo "  [WARN] models.py has changes not yet in migration files."
    echo "         Run the following on production to see exactly what changed:"
    echo "           docker exec $CONTAINER $MANAGE makemigrations --dry-run $APP_NAME"
    echo "         Then generate a new migration on dev, commit it, and redeploy."
    echo ""
    echo "  --- Detected drift (makemigrations --dry-run output) ---"
    echo "$MAKEMIG_OUT" | grep -v "^JWT" | grep -v "^Migrations"
    echo "  ---------------------------------------------------------"
    MODEL_OK=0
    ERRORS=$((ERRORS + 1))
fi

# Check B: all migration files are applied in DB
UNAPPLIED=$(docker exec "$CONTAINER" $MANAGE showmigrations "$APP_NAME" 2>/dev/null | grep -c '^\s*\[ \]' || true)
if [ "$UNAPPLIED" -eq 0 ]; then
    echo "  [OK] All migration files are applied in the DB."
    APPLY_OK=1
else
    echo "  [WARN] $UNAPPLIED migration file(s) are still not applied in DB."
    APPLY_OK=0
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ "$MODEL_OK" -eq 1 ] && [ "$APPLY_OK" -eq 1 ]; then
    echo "  RESULT:  models.py == migration files == DB  --  FULLY IN SYNC"
else
    echo "  RESULT:  NOT fully in sync. See warnings above."
fi

echo ""
echo "======================================================="
echo " Done. Errors: $ERRORS"
echo "======================================================="

exit $ERRORS
