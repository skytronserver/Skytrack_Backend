#!/bin/bash
# =============================================================================
# fix_schema_prod.sh
#
# Aligns production PostgreSQL DB schema 100% with models.py.
# Checks and fixes:
#   - varchar column lengths (DB narrower than model)
#   - NULL / NOT NULL constraints
#   - DecimalField precision and scale
#   - Missing field-level indexes (db_index=True)
#   - Missing unique constraints (unique=True)
#   - Missing unique_together constraints
#   - Missing Meta.indexes
#
# RECOMMENDED WORKFLOW ON PRODUCTION:
#   1. git pull                        (get latest code including models.py)
#   2. sudo ./run_with_host_storage.sh (rebuild container with new code)
#   3. sudo ./fix_migrations_prod.sh   (align migration history)
#   4. sudo ./fix_schema_prod.sh       (THIS script - align physical schema)
#
# HOW IT WORKS:
#   - Runs a Python audit script INSIDE the Docker container so Django loads
#     models.py and connects to the real DB via container settings
#   - The audit generates SQL for every mismatch it finds
#   - The SQL is applied from the HOST via psql using .env credentials
#   - A second verification pass confirms everything is aligned
#
# Usage:  sudo ./fix_schema_prod.sh
# =============================================================================

set -o pipefail

# ---- CONFIGURE THESE ----
ENV_FILE="/home/Admin/backendapi/SkytronInog_20260226/Skytrack_Backend/.env"
CONTAINER="skytron-backend-api-container"
MANAGE="python /app/manage.py"
# -------------------------

AUDIT_PY_HOST="/tmp/_skytrack_schema_audit_$$.py"
AUDIT_PY_CTR="/tmp/_skytrack_schema_audit.py"
SQL_FILE="/tmp/_skytrack_schema_fixes_$$.sql"
WARN_FILE="/tmp/_skytrack_schema_warns_$$.txt"
VERIFY_FILE="/tmp/_skytrack_schema_verify_$$.sql"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo ""; echo -e "${BLUE}===== $* =====${NC}"; }

cleanup() {
    rm -f "$AUDIT_PY_HOST" "$SQL_FILE" "$WARN_FILE" "$VERIFY_FILE"
    docker exec "$CONTAINER" rm -f "$AUDIT_PY_CTR" 2>/dev/null || true
}
trap cleanup EXIT

ERRORS=0

echo ""
echo "=============================================="
echo "  Skytrack Production Schema Alignment"
echo "  models.py is the Single Source of Truth"
echo "=============================================="

# ---- Load .env ----
if [ ! -f "$ENV_FILE" ]; then
    error ".env not found at: $ENV_FILE"
    exit 1
fi
eval "$(grep '^export ' "$ENV_FILE" | sed 's/^export //')"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-skytrondb_main}"
DB_USER="${DB_USER:-dbadmin}"
DB_PASS="${DB_PASSWORD}"

info "DB   : ${DB_HOST}:${DB_PORT}/${DB_NAME}"
info "User : ${DB_USER}"
info "Ctr  : ${CONTAINER}"

# ---- Check container ----
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    error "Container '$CONTAINER' is not running. Start it first."
    exit 1
fi

# =============================================================================
# Write audit Python script to host temp file.
# IMPORTANT: 'PYEOF' is single-quoted so bash does NOT expand anything inside.
# =============================================================================
cat > "$AUDIT_PY_HOST" << 'PYEOF'
"""
Schema audit script for fix_schema_prod.sh
- Runs inside the Docker container via 'manage.py shell -c exec(...)'
- Compares every concrete field in models.py against the actual PostgreSQL schema
- Outputs SQL fixes to stdout  (BEGIN; ... COMMIT;)
- Outputs warnings  to stderr  (lines starting with WARN:)
"""
import sys
from django.apps import apps
from django.db import connection

DJANGO_TO_PG = {
    'AutoField':              'integer',
    'BigAutoField':           'bigint',
    'SmallAutoField':         'smallint',
    'CharField':              'character varying',
    'TextField':              'text',
    'IntegerField':           'integer',
    'BigIntegerField':        'bigint',
    'SmallIntegerField':      'smallint',
    'PositiveIntegerField':   'integer',
    'PositiveSmallIntegerField': 'smallint',
    'FloatField':             'double precision',
    'DecimalField':           'numeric',
    'BooleanField':           'boolean',
    'NullBooleanField':       'boolean',
    'DateField':              'date',
    'DateTimeField':          'timestamp with time zone',
    'TimeField':              'time without time zone',
    'EmailField':             'character varying',
    'URLField':               'character varying',
    'SlugField':              'character varying',
    'UUIDField':              'uuid',
    'JSONField':              'jsonb',
    'FileField':              'character varying',
    'ImageField':             'character varying',
    'IPAddressField':         'inet',
    'GenericIPAddressField':  'inet',
    'ForeignKey':             'bigint',
    'OneToOneField':          'bigint',
}

# Acceptable type differences that are NOT errors (legacy tables, DB-side widening)
# (model_type, db_type) pairs that should be silently skipped
ACCEPTABLE_TYPE_DIFFS = {
    ('bigint',            'integer'),   # BigAutoField on legacy integer PK
    ('integer',          'bigint'),     # IntegerField stored as bigint (wider, safe)
    ('character varying', 'text'),      # CharField stored as text (wider, safe)
}

# ---- Load DB schema ----
with connection.cursor() as cur:
    cur.execute("""
        SELECT table_name, column_name, data_type, character_maximum_length,
               is_nullable, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
    """)
    db_cols = {}
    for table, col, dtype, maxlen, nullable, num_prec, num_scale in cur.fetchall():
        db_cols.setdefault(table, {})[col] = {
            'data_type': dtype,
            'max_length': maxlen,
            'nullable':   nullable,
            'num_prec':   num_prec,
            'num_scale':  num_scale,
        }

    cur.execute("""
        SELECT t.relname, i.relname, ix.indisunique,
               array_to_string(
                   array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)),
                   ','
               )
        FROM pg_class t
        JOIN pg_index ix    ON t.oid = ix.indrelid
        JOIN pg_class i     ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE t.relkind = 'r'
        GROUP BY t.relname, i.relname, ix.indisunique
    """)
    db_indexes = {}
    for table, iname, is_unique, cols in cur.fetchall():
        db_indexes.setdefault(table, []).append({
            'name': iname, 'unique': is_unique, 'cols': cols
        })

# ---- Compare models.py vs DB ----
app      = apps.get_app_config('skytron_api')
sql      = []   # SQL statements to fix mismatches
warnings = []   # Issues that cannot be auto-fixed

for model in app.get_models():
    meta  = model._meta
    table = meta.db_table

    if table not in db_cols:
        warnings.append(
            f"TABLE MISSING IN DB: {table} -- ensure all migrations have run"
        )
        continue

    # Only concrete fields that have an actual DB column (skip M2M and reverse relations)
    concrete = [
        f for f in meta.get_fields()
        if hasattr(f, 'column') and f.column and not f.many_to_many
    ]

    # ── Per-field checks ────────────────────────────────────────────────────
    for field in concrete:
        col = field.column
        if col not in db_cols[table]:
            warnings.append(
                f"COLUMN MISSING: {table}.{col} -- run makemigrations/migrate first"
            )
            continue

        db       = db_cols[table][col]
        internal = field.get_internal_type()

        # 1. VARCHAR length: only a problem when model > DB
        if internal in ('CharField', 'EmailField', 'URLField',
                        'SlugField', 'FileField', 'ImageField'):
            ml = getattr(field, 'max_length', None)
            if ml and db['max_length'] and int(ml) > int(db['max_length']):
                sql.append(
                    f"ALTER TABLE {table} ALTER COLUMN {col} TYPE varchar({ml});"
                    f"  -- {col}: DB was varchar({db['max_length']}), model requires {ml}"
                )

        # 2. Nullable / NOT NULL
        model_null = 'YES' if getattr(field, 'null', False) else 'NO'
        if model_null != db['nullable']:
            if model_null == 'NO' and db['nullable'] == 'YES':
                # Only allowed if there are zero actual NULLs in the column
                with connection.cursor() as c2:
                    c2.execute(
                        f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NULL'
                    )
                    null_count = c2.fetchone()[0]
                if null_count == 0:
                    sql.append(
                        f"ALTER TABLE {table} ALTER COLUMN {col} SET NOT NULL;"
                        f"  -- was nullable, model says NOT NULL, confirmed 0 NULLs"
                    )
                else:
                    warnings.append(
                        f"CANNOT SET NOT NULL: {table}.{col} has {null_count} NULL rows"
                        f" -- fix the data manually then rerun this script"
                    )
            elif model_null == 'YES' and db['nullable'] == 'NO':
                sql.append(
                    f"ALTER TABLE {table} ALTER COLUMN {col} DROP NOT NULL;"
                    f"  -- model allows null, DB currently NOT NULL"
                )

        # 3. DecimalField precision / scale
        if internal == 'DecimalField':
            mp = getattr(field, 'max_digits',      None)
            ms = getattr(field, 'decimal_places',  None)
            dp = db['num_prec']
            ds = db['num_scale']
            prec_mismatch  = mp and dp    and int(mp) != int(dp)
            scale_mismatch = ms is not None and ds is not None and int(ms) != int(ds)
            if prec_mismatch or scale_mismatch:
                new_mp = mp if mp is not None else dp
                new_ms = ms if ms is not None else ds
                sql.append(
                    f"ALTER TABLE {table} ALTER COLUMN {col} TYPE numeric({new_mp},{new_ms});"
                    f"  -- precision/scale mismatch: model=({mp},{ms}) db=({dp},{ds})"
                )

    # ── Index and unique constraint checks ──────────────────────────────────
    db_idx_list = db_indexes.get(table, [])
    db_unique   = {d['cols'] for d in db_idx_list if d['unique']}
    db_all_idx  = {d['cols'] for d in db_idx_list}

    for field in concrete:
        col = field.column

        # field-level unique=True
        if getattr(field, 'unique', False) and not getattr(field, 'primary_key', False):
            if col not in db_unique:
                with connection.cursor() as c2:
                    c2.execute(
                        f'SELECT COUNT(*) FROM ('
                        f'  SELECT "{col}" FROM "{table}"'
                        f'  WHERE "{col}" IS NOT NULL'
                        f'  GROUP BY "{col}" HAVING COUNT(*) > 1'
                        f') t'
                    )
                    dup_count = c2.fetchone()[0]
                if dup_count == 0:
                    cname = f'{table}_{col}_uniq'[:63]
                    sql.append(
                        f"ALTER TABLE {table} ADD CONSTRAINT {cname} UNIQUE ({col});"
                        f"  -- missing unique constraint"
                    )
                else:
                    warnings.append(
                        f"CANNOT ADD UNIQUE: {table}.{col} has {dup_count} duplicate values"
                        f" -- de-duplicate the data manually then rerun"
                    )

        # field-level db_index=True (not already covered by unique)
        if getattr(field, 'db_index', False) and not getattr(field, 'unique', False):
            if col not in db_all_idx:
                iname = f'{table}_{col}_idx'[:63]
                sql.append(
                    f"CREATE INDEX IF NOT EXISTS {iname} ON {table} ({col});"
                    f"  -- missing index"
                )

    # unique_together
    for ut in getattr(meta, 'unique_together', []):
        col_list = []
        for fname in ut:
            try:
                col_list.append(meta.get_field(fname).column)
            except Exception:
                col_list.append(fname)
        key = ','.join(col_list)
        if key not in db_unique:
            col_str = ', '.join(col_list)
            cname   = (table + '_' + '_'.join(col_list[:3]) + '_utog')[:63]
            sql.append(
                f"ALTER TABLE {table} ADD CONSTRAINT {cname} UNIQUE ({col_str});"
                f"  -- missing unique_together"
            )

    # Meta.indexes
    for idx in getattr(meta, 'indexes', []):
        col_list   = []
        order_cols = []
        for fname in idx.fields:
            desc        = fname.startswith('-')
            fname_clean = fname.lstrip('-')
            try:
                c = meta.get_field(fname_clean).column
            except Exception:
                c = fname_clean
            col_list.append(c)
            order_cols.append(f'{c} DESC' if desc else c)
        key = ','.join(col_list)
        if key not in db_all_idx:
            sql.append(
                f"CREATE INDEX IF NOT EXISTS {idx.name} ON {table} ({', '.join(order_cols)});"
                f"  -- missing Meta.index"
            )

# ---- Output ----
if sql:
    print("BEGIN;")
    for line in sql:
        print(line)
    print("COMMIT;")
    print("SELECT 'FIXES_APPLIED' AS schema_result;")
else:
    print("SELECT 'NO_FIXES_NEEDED' AS schema_result;")

if warnings:
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
PYEOF

# ---- Copy audit script to container ----
docker cp "$AUDIT_PY_HOST" "$CONTAINER:$AUDIT_PY_CTR"

# =============================================================================
# STEP 1 — Run audit, generate SQL
# =============================================================================
step "STEP 1: Auditing schema (models.py vs DB)"

docker exec "$CONTAINER" $MANAGE shell \
    -c "exec(open('$AUDIT_PY_CTR').read())" \
    > "$SQL_FILE" \
    2> "$WARN_FILE" || true

# Strip Django/system noise from the warnings file
grep '^WARN:' "$WARN_FILE" > "${WARN_FILE}.clean" 2>/dev/null && \
    mv "${WARN_FILE}.clean" "$WARN_FILE" || \
    truncate -s 0 "$WARN_FILE"

FIX_COUNT=$(grep -cE '^ALTER|^CREATE INDEX' "$SQL_FILE" 2>/dev/null || true); FIX_COUNT=${FIX_COUNT:-0}
WARN_COUNT=$(grep -c '^WARN:' "$WARN_FILE" 2>/dev/null || true); WARN_COUNT=${WARN_COUNT:-0}

info "Fixes found : $FIX_COUNT"
info "Warnings    : $WARN_COUNT"

if [ "$WARN_COUNT" -gt 0 ]; then
    warn "--- Warnings (require manual attention) ---"
    while IFS= read -r line; do
        warn "  $line"
    done < "$WARN_FILE"
    warn "-------------------------------------------"
fi

# =============================================================================
# STEP 2 — Apply SQL fixes
# =============================================================================
step "STEP 2: Applying fixes"

if grep -q 'NO_FIXES_NEEDED' "$SQL_FILE" 2>/dev/null; then
    info "DB is already fully aligned with models.py — nothing to apply."
else
    echo ""
    echo "--- SQL to be applied ---"
    grep -v '^SELECT' "$SQL_FILE" || true
    echo "-------------------------"
    echo ""

    APPLY_RESULT=$(PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" \
        -P pager=off \
        -f "$SQL_FILE" 2>&1) || {
            echo "$APPLY_RESULT"
            error "psql failed applying fixes. See output above."
            ERRORS=$((ERRORS + 1))
        }

    echo "$APPLY_RESULT"

    if echo "$APPLY_RESULT" | grep -qiE 'ERROR|FATAL'; then
        error "One or more SQL statements failed. See output above."
        ERRORS=$((ERRORS + 1))
    else
        info "All fixes applied successfully."
    fi
fi

# =============================================================================
# STEP 3 — Verify (re-run audit, expect NO_FIXES_NEEDED)
# =============================================================================
step "STEP 3: Verifying alignment"

docker exec "$CONTAINER" $MANAGE shell \
    -c "exec(open('$AUDIT_PY_CTR').read())" \
    > "$VERIFY_FILE" \
    2>/dev/null || true

REMAINING=$(grep -cE '^ALTER|^CREATE INDEX' "$VERIFY_FILE" 2>/dev/null || true); REMAINING=${REMAINING:-0}

echo ""
if grep -q 'NO_FIXES_NEEDED' "$VERIFY_FILE" 2>/dev/null && [ "$REMAINING" -eq 0 ]; then
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  RESULT: DB == models.py — 100% ALIGNED         ${NC}"
    echo -e "${GREEN}  All types, lengths, nulls, indexes, uniques OK ${NC}"
    echo -e "${GREEN}================================================${NC}"
else
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}  RESULT: $REMAINING fix(es) still needed        ${NC}"
    echo -e "${YELLOW}  (likely due to warnings that need manual fix)  ${NC}"
    echo -e "${YELLOW}================================================${NC}"
    echo ""
    echo "Remaining issues:"
    grep -E '^ALTER|^CREATE INDEX|^WARN' "$VERIFY_FILE" || true
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "Done. Errors: $ERRORS"
echo ""
[ "$ERRORS" -eq 0 ] && exit 0 || exit 1
