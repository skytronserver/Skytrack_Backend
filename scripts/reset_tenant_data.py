"""
Production data reset: delete every non-superadmin account and all data hanging
off them, keeping superadmin accounts and permanent/master data.

Run inside the API container through `manage.py shell` (stdin):

  DRY RUN (default, changes nothing, prints the plan + row counts):
    docker exec -i skytron-backend-api-container python manage.py shell < scripts/reset_tenant_data.py

  EXECUTE (single transaction, rolls back completely on any error):
    docker exec -i -e RESET_CONFIRM=DELETE-ALL-TENANT-DATA \
        skytron-backend-api-container python manage.py shell < scripts/reset_tenant_data.py

Optional env vars (pass with -e):
  RESET_SUPERADMIN_EMAIL  superadmin that inherits NOT NULL created_by-style links on
                          kept rows (default: the lowest-id superadmin)
  RESET_KEEP_LOGS=1       do not truncate raw log tables (GPSDataLog, RequestLog, ...)
  RESET_SKIP_CACHE=1      do not flush the Django Redis cache after commit
  RESET_REPORT_ONLY=1     only print what every table currently holds (changes nothing)
  RESET_LOCK_TIMEOUT      Postgres lock_timeout, default '60s'

What it does (all at SQL level, one transaction):
  1. Users kept   = role 'superadmin' OR is_superuser = true.
  2. KEEP tables  (states, districts, POI, vehicle categories, permits, public bus
                   stops/routes, bus stands, RBAC, OTA command catalogue, onboarding
                   test cases, global settings, ...) keep every row. Their FK columns
                   that point at a user being deleted are re-pointed: nullable -> NULL,
                   NOT NULL -> the chosen superadmin. (Needed because e.g.
                   pointofinterests.created_by is ON DELETE CASCADE in Django.)
  3. USER-SCOPED tables (login sessions, tokens, notices, admin log, user<->group)
                   lose only the rows of deleted users; superadmin rows stay.
  4. Every other table of the project apps is TRUNCATEd (manufacturers, dealers,
     eSIM providers, owners, state admins, DTO/RTO, SOS admins/teams/executives,
     test agencies, schools, device models, device stock, device tags, GPS data,
     alerts, emergency calls, tickets, whitelists, ...).
  5. Non-superadmin users are deleted.
  Sequences are NOT reset, so old ids are never reused by new rows.
  At the end it prints a FINAL REPORT: every table, rows before/after, size after.
  Tip: append `| tee reset_report_$(date +%F_%H%M).txt` to keep the output.
"""
import os
import sys
import time

from django.apps import apps
from django.core.cache import cache
from django.db import connection, transaction

CONFIRM_PHRASE = "DELETE-ALL-TENANT-DATA"
EXECUTE = os.environ.get("RESET_CONFIRM") == CONFIRM_PHRASE
KEEP_LOGS = os.environ.get("RESET_KEEP_LOGS") == "1"
SKIP_CACHE = os.environ.get("RESET_SKIP_CACHE") == "1"
REPORT_ONLY = os.environ.get("RESET_REPORT_ONLY") == "1"
LOCK_TIMEOUT = os.environ.get("RESET_LOCK_TIMEOUT", "60s")
SUPERADMIN_EMAIL = os.environ.get("RESET_SUPERADMIN_EMAIL", "").strip()

# Apps whose tables are considered at all. Anything outside these is left untouched.
PROJECT_APPS = {"skytron_api", "admin", "sessions", "authtoken"}

# ---- Permanent / master data: every row is kept --------------------------------
KEEP_MODELS = {
    # geography & vehicle masters
    "skytron_api.Settings_State",
    "skytron_api.Settings_District",
    "skytron_api.Settings_VehicleCategory",
    "skytron_api.Settings_VehicleCategoryCode",
    "skytron_api.Settings_PermitMaster",
    "skytron_api.PermitCondition",
    # points of interest / public transport masters
    "skytron_api.pointofinterests",
    "skytron_api.BusStand",
    "skytron_api.PublicBusStop",
    "skytron_api.PublicBusRoute",
    "skytron_api.PublicRouteStop",
    # RBAC
    "skytron_api.UserRoleType",
    "skytron_api.RolePermissionConfig",
    # catalogues / global configuration
    "skytron_api.OTACommandDefinition",
    "skytron_api.OTACommandValueSuggestion",
    "skytron_api.TechnicalOnboardingTestCase",
    "skytron_api.TestAgencyDetails",
    "skytron_api.Settings",
    "skytron_api.LoginSettings",
    "skytron_api.IPList",
    "skytron_api.FOTA",
    "skytron_api.VahanDummyData",
    # kept so tokens of superadmins that logged out stay revoked
    "skytron_api.TokenBlacklist",
}

# ---- Only rows belonging to deleted users are removed ------------------------
# model label -> FK column (to User) used to decide ownership
USER_SCOPED_MODELS = {
    "skytron_api.Session": "user_id",
    "skytron_api.Notice": "createdby_id",
    "skytron_api.OTASettings": "triggered_by_id",
    "authtoken.Token": "user_id",
    "admin.LogEntry": "user_id",
}

# ---- Raw log tables (cleared unless RESET_KEEP_LOGS=1) -----------------------
LOG_MODELS = {
    "skytron_api.GPSDataLog",
    "skytron_api.GPSemDataLog",
    "skytron_api.RequestLog",
    "skytron_api.RequestLogaaaaa",
    "skytron_api.Captcha",
    "skytron_api.sms_in",
    "skytron_api.sms_out",
    "skytron_api.BleSosAppLog",
    "skytron_api.AirtelSmsInLog",
    "skytron_api.SmppSmsOut",
    "skytron_api.SmppSmsPart",
    "skytron_api.SmppSmsIn",
}

User = apps.get_model("skytron_api", "User")
USER_TABLE = User._meta.db_table


def q(name):
    return connection.ops.quote_name(name)


def out(msg=""):
    print(msg, flush=True)


def fail(msg):
    out(f"\nABORTED: {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Build table classification
# ---------------------------------------------------------------------------
label_by_table = {}
for m in apps.get_models(include_auto_created=True):
    if m._meta.app_label not in PROJECT_APPS or m._meta.proxy or not m._meta.managed:
        continue
    label_by_table.setdefault(m._meta.db_table, m._meta.label)

keep_tables, user_scoped, clear_tables = set(), {}, set()
user_m2m_tables = {}  # through table -> column pointing at User

for m in apps.get_models():
    for f in m._meta.local_many_to_many:
        through = f.remote_field.through
        if not through._meta.auto_created:
            continue
        t = through._meta.db_table
        if m._meta.label in KEEP_MODELS:
            keep_tables.add(t)
        elif m is User:
            # skytron_api_user_groups / _user_permissions: drop rows of deleted users
            user_m2m_tables[t] = f.m2m_column_name()

for table, label in label_by_table.items():
    if table in keep_tables or table in user_m2m_tables:
        continue
    if table == USER_TABLE or label in KEEP_MODELS:
        keep_tables.add(table)
    elif label in USER_SCOPED_MODELS:
        user_scoped[table] = USER_SCOPED_MODELS[label]
    elif KEEP_LOGS and label in LOG_MODELS:
        keep_tables.add(table)
    else:
        clear_tables.add(table)
keep_tables.discard(USER_TABLE)
user_scoped.update(user_m2m_tables)

# Sanity: every configured label must exist (catches typos / renamed models)
known_labels = set(label_by_table.values())
missing = (KEEP_MODELS | set(USER_SCOPED_MODELS) | LOG_MODELS) - known_labels
if missing:
    fail(f"configured models not found: {sorted(missing)}")

# ---------------------------------------------------------------------------
# Foreign keys straight from the Postgres catalog (covers partitions, manual FKs)
# ---------------------------------------------------------------------------
with connection.cursor() as cur:
    cur.execute(
        """
        SELECT src.relname, a.attname, NOT a.attnotnull AS nullable, dst.relname
        FROM pg_constraint c
        JOIN pg_class src ON src.oid = c.conrelid
        JOIN pg_class dst ON dst.oid = c.confrelid
        JOIN pg_namespace n ON n.oid = src.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f' AND n.nspname = current_schema()
        """
    )
    fks = cur.fetchall()

# TRUNCATE fails if any table that is NOT truncated has an FK to a truncated one.
blockers = [(s, col, d) for s, col, _, d in fks if d in clear_tables and s not in clear_tables]
if blockers:
    lines = "\n".join(f"  {s}.{col} -> {d}" for s, col, d in sorted(blockers))
    fail("these kept tables reference tables that would be truncated; "
         "classify them consistently first:\n" + lines)

# FK columns into the user table from kept / user-scoped tables
user_refs = [(s, col, nullable) for s, col, nullable, d in fks
             if d == USER_TABLE and s not in clear_tables and s != USER_TABLE]
unknown_refs = [r for r in user_refs if r[0] not in keep_tables and r[0] not in user_scoped]
if unknown_refs:
    fail("tables outside the plan reference users; add them to the script: "
         + ", ".join(f"{s}.{c}" for s, c, _ in unknown_refs))

# ---------------------------------------------------------------------------
# Plan / counts
# ---------------------------------------------------------------------------
def count(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


EXACT_LIMIT = 200_000  # below this an exact count(*) is cheap; above it use the planner estimate


def rows_of(cur, table):
    """(rows, exact) -- exact count for small tables, pg estimate for big ones."""
    cur.execute("SELECT GREATEST(reltuples, 0)::bigint FROM pg_class "
                "WHERE relname = %s AND relnamespace = current_schema()::regnamespace", [table])
    r = cur.fetchone()
    approx = r[0] if r else 0
    if approx < EXACT_LIMIT:  # small or never-analysed table
        return count(cur, f"SELECT count(*) FROM {q(table)}"), True
    return approx, False


def estimate(cur, table):
    return rows_of(cur, table)[0]


def snapshot(cur):
    """Every ordinary/partitioned table of the schema -> (rows, exact, bytes)."""
    cur.execute(
        """
        SELECT c.relname, pg_total_relation_size(c.oid)
        FROM pg_class c
        WHERE c.relnamespace = current_schema()::regnamespace
          AND c.relkind IN ('r', 'p') AND NOT c.relispartition
        """
    )
    sizes = cur.fetchall()
    snap = {}
    for t, size in sizes:
        n, exact = rows_of(cur, t)
        snap[t] = (n, exact, size)
    return snap


def action_of(t):
    if t == USER_TABLE:
        return "USERS (superadmins only)"
    if t in clear_tables:
        return "PURGED (TRUNCATE)"
    if t in user_scoped:
        return "USER-SCOPED (deleted users' rows removed)"
    if t in keep_tables:
        return "KEPT (permanent data)"
    return "UNTOUCHED (outside plan: Django/system)"


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or unit == "TB":
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024


def fmt_rows(n, exact):
    return f"{n:,}" if exact else f"~{n:,}"


def print_report(title, after, before=None):
    out("\n" + "=" * 100)
    out(title)
    out("=" * 100)
    groups = {}
    for t in after:
        groups.setdefault(action_of(t), []).append(t)
    order = ["USERS (superadmins only)", "KEPT (permanent data)",
             "USER-SCOPED (deleted users' rows removed)", "PURGED (TRUNCATE)",
             "UNTOUCHED (outside plan: Django/system)"]
    for g in order:
        tables = sorted(groups.get(g, []))
        if not tables:
            continue
        out(f"\n[{g}]  {len(tables)} tables")
        if before is not None:
            out(f"  {'table':<52} {'rows before':>14} {'rows after':>14} {'size after':>11}")
        else:
            out(f"  {'table':<52} {'rows':>14} {'size':>11}")
        empty = []
        for t in tables:
            n, exact, size = after[t]
            if before is not None:
                bn, bexact, _ = before.get(t, (0, True, 0))
                if n == 0 and bn == 0:
                    empty.append(t)
                    continue
                out(f"  {t:<52} {fmt_rows(bn, bexact):>14} {fmt_rows(n, exact):>14} {human(size):>11}")
            else:
                if n == 0:
                    empty.append(t)
                    continue
                out(f"  {t:<52} {fmt_rows(n, exact):>14} {human(size):>11}")
        if empty:
            out(f"  (+ {len(empty)} tables already empty: {', '.join(empty)})")
    non_empty = [t for t, (n, _, _) in after.items() if n]
    out(f"\nTables with data: {len(non_empty)} of {len(after)}")
    with connection.cursor() as c2:
        c2.execute(f"SELECT role, count(*) FROM {q(USER_TABLE)} GROUP BY role ORDER BY 1")
        out("Users by role: " + ", ".join(f"{r}={n}" for r, n in c2.fetchall()))
        c2.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        out(f"Database size now: {c2.fetchone()[0]}")
    out("(~ = planner estimate for tables over 200k rows)")


def keep_where(alias=""):
    p = f"{alias}." if alias else ""
    return f"({p}role = 'superadmin' OR {p}is_superuser)"


keep_user_where = keep_where()

if REPORT_ONLY:
    with connection.cursor() as cur:
        print_report(f"CURRENT CONTENT OF {connection.settings_dict['NAME']} (report only, nothing changed)",
                     snapshot(cur))
    sys.exit(0)

with connection.cursor() as cur:
    cur.execute(f"SELECT id, email, role FROM {q(USER_TABLE)} WHERE {keep_user_where} ORDER BY id")
    superadmins = cur.fetchall()
    if not superadmins:
        fail("no superadmin account found; refusing to delete every user")
    if SUPERADMIN_EMAIL:
        heir = next((s for s in superadmins if s[1].lower() == SUPERADMIN_EMAIL.lower()), None)
        if not heir:
            fail(f"RESET_SUPERADMIN_EMAIL {SUPERADMIN_EMAIL!r} is not a kept superadmin")
    else:
        heir = superadmins[0]
    heir_id = heir[0]

    cur.execute(f"SELECT role, count(*) FROM {q(USER_TABLE)} WHERE NOT {keep_user_where} "
                "GROUP BY role ORDER BY 2 DESC")
    doomed_by_role = cur.fetchall()

    out("=" * 72)
    out(f"DATABASE: {connection.settings_dict['NAME']} @ {connection.settings_dict['HOST'] or 'local'}")
    out(f"MODE    : {'EXECUTE' if EXECUTE else 'DRY RUN (nothing will change)'}")
    out("=" * 72)
    out(f"\nUsers KEPT ({len(superadmins)}):")
    for sid, email, role in superadmins:
        out(f"  #{sid:<6} {email:<40} {role}{'   <- inherits re-pointed links' if sid == heir_id else ''}")
    out("\nUsers DELETED by role:")
    for role, n in doomed_by_role:
        out(f"  {role or '(blank)':<20} {n}")
    out(f"  {'TOTAL':<20} {sum(n for _, n in doomed_by_role)}")

    out("\nKEEP tables: kept rows that point at deleted users are re-pointed:")
    for s, col, nullable in sorted(user_refs):
        if s not in keep_tables:
            continue
        n = count(cur, f"SELECT count(*) FROM {q(s)} t JOIN {q(USER_TABLE)} u ON u.id = t.{q(col)} "
                       f"WHERE NOT {keep_where('u')}")
        out(f"  {s}.{col:<28} {n:>8} rows -> {'NULL' if nullable else f'user #{heir_id}'}")

    out("\nUSER-SCOPED tables: rows of deleted users removed:")
    for t, col in sorted(user_scoped.items()):
        n = count(cur, f"SELECT count(*) FROM {q(t)} WHERE {q(col)} IN "
                       f"(SELECT id FROM {q(USER_TABLE)} WHERE NOT {keep_user_where})")
        out(f"  {t:<52} {n:>10}")

    before = snapshot(cur)
    out("\nPURGED tables (TRUNCATE: whole table emptied at once, disk freed immediately):")
    total = total_size = 0
    for t in sorted(clear_tables):
        n, exact, size = before.get(t, (0, True, 0))
        total += n
        total_size += size
        out(f"  {t:<52} {fmt_rows(n, exact):>14} {human(size):>11}")
    out(f"  {'TOTAL':<52} {total:>14,} {human(total_size):>11}")

    out("\nKEPT tables (untouched rows):")
    for t in sorted(keep_tables):
        out(f"  {t}")

if not EXECUTE:
    out("\nDry run only. To execute, re-run with -e RESET_CONFIRM=" + CONFIRM_PHRASE)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
out("\nExecuting ...")
t_start = time.monotonic()


def step_done(msg, t0):
    out(f"  {msg}  [{time.monotonic() - t0:.1f}s]")


doomed = f"SELECT id FROM {q(USER_TABLE)} WHERE NOT {keep_user_where}"
with transaction.atomic():
    with connection.cursor() as cur:
        cur.execute(f"SET LOCAL lock_timeout = %s", [LOCK_TIMEOUT])
        cur.execute("SET LOCAL statement_timeout = 0")

        # 1. purge everything that hangs off tenants. TRUNCATE drops the table files
        #    instead of deleting row by row, so 28M-row GPS logs clear in seconds;
        #    one statement for all tables so FKs between them are fine.
        if clear_tables:
            t0 = time.monotonic()
            cur.execute("TRUNCATE TABLE " + ", ".join(q(t) for t in sorted(clear_tables)))
            step_done(f"purged {len(clear_tables)} tables with TRUNCATE", t0)

        # 2. re-point kept rows away from users about to be deleted
        t0 = time.monotonic()
        for s, col, nullable in sorted(user_refs):
            if s not in keep_tables:
                continue
            value = "NULL" if nullable else str(int(heir_id))
            cur.execute(f"UPDATE {q(s)} SET {q(col)} = {value} WHERE {q(col)} IN ({doomed})")
            if cur.rowcount:
                out(f"  re-pointed {cur.rowcount} rows in {s}.{col}")
        step_done("re-pointed kept rows", t0)

        # 3. user-scoped rows (small tables: row delete, superadmin rows stay)
        t0 = time.monotonic()
        for t, col in sorted(user_scoped.items()):
            cur.execute(f"DELETE FROM {q(t)} WHERE {q(col)} IN ({doomed})")
            if cur.rowcount:
                out(f"  deleted {cur.rowcount} rows from {t}")
        step_done("removed deleted users' sessions/tokens/notices", t0)

        # 4. the users themselves
        t0 = time.monotonic()
        cur.execute(f"DELETE FROM {q(USER_TABLE)} WHERE NOT {keep_user_where}")
        step_done(f"deleted {cur.rowcount} users", t0)

        left = count(cur, f"SELECT count(*) FROM {q(USER_TABLE)}")
        if left != len(superadmins):
            raise RuntimeError(f"expected {len(superadmins)} users left, found {left}; rolling back")

out(f"COMMITTED in {time.monotonic() - t_start:.1f}s.")

if not SKIP_CACHE:
    try:
        cache.clear()
        out("Django Redis cache flushed (all logged-in sessions incl. superadmins must log in again).")
    except Exception as exc:  # cache failure must not hide the committed DB result
        out(f"WARNING: cache flush failed: {exc}. Flush Redis DB 1 manually.")

with connection.cursor() as cur:
    for t in sorted(keep_tables | set(user_scoped) | {USER_TABLE}):
        cur.execute(f"ANALYZE {q(t)}")  # refresh estimates so the report is accurate
    print_report("FINAL REPORT: database content after the reset", snapshot(cur), before)

out("\nDone. Restart the API / MQTT / GPS / EM containers so no stale in-memory state remains.")
