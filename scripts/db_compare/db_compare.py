"""
Compare a Skytron database (schema + RBAC configuration) against a reference.

Run inside the backend container through `manage.py shell`:

  Export a reference (on dev):
    docker exec -e MODE=export -e REF=/tmp/ref.json <container> \
        sh -c "python manage.py shell < /tmp/db_compare.py"

  Compare against it (on NIC):
    docker exec -e MODE=compare -e REF=/tmp/ref.json <container> \
        sh -c "python manage.py shell < /tmp/db_compare.py"

Read-only: only SELECTs against information_schema / pg_catalog and the RBAC tables.
"""
import json
import os
import re

from django.db import connection

MODE = os.environ.get('MODE', 'compare')
REF = os.environ.get('REF', '/tmp/ref.json')


def q(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchall()


def snapshot():
    snap = {}

    snap['extensions'] = sorted(n for (n,) in q("SELECT extname FROM pg_extension"))

    cols = {}
    for t, col, typ, length, prec, scale, nullable, default in q("""
        SELECT table_name, column_name, data_type, character_maximum_length,
               numeric_precision, numeric_scale, is_nullable, column_default
        FROM information_schema.columns WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position"""):
        spec = typ
        if length:
            spec += f"({length})"
        elif typ == 'numeric' and prec:
            spec += f"({prec},{scale})"
        spec += ' NULL' if nullable == 'YES' else ' NOT NULL'
        if default and 'nextval(' not in default:     # serial sequences differ only by name
            spec += f" DEFAULT {default}"
        cols.setdefault(t, {})[col] = spec
    tables = {t for (t,) in q("SELECT table_name FROM information_schema.tables "
                             "WHERE table_schema='public' AND table_type='BASE TABLE'")}
    snap['tables'] = {t: cols.get(t, {}) for t in sorted(tables)}

    # Constraints, keyed by their definition (names can differ between databases)
    cons = {}
    for t, ctype, definition in q("""
        SELECT rel.relname, con.contype, pg_get_constraintdef(con.oid)
        FROM pg_constraint con JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = rel.relnamespace
        WHERE n.nspname = 'public' AND con.contype IN ('p', 'u', 'f', 'c')"""):
        kind = {'p': 'PK', 'u': 'UNIQUE', 'f': 'FK', 'c': 'CHECK'}[ctype]
        definition = re.sub(r'\s+', ' ', definition)
        definition = re.sub(r' DEFERRABLE INITIALLY DEFERRED', '', definition)
        cons.setdefault(t, []).append(f"{kind} {definition}")
    snap['constraints'] = {t: sorted(v) for t, v in sorted(cons.items())}

    # Indexes, keyed by definition with the index name stripped
    idx = {}
    for t, definition in q("SELECT tablename, indexdef FROM pg_indexes WHERE schemaname = 'public'"):
        definition = re.sub(r'INDEX \S+ ON ', 'INDEX ON ', definition)
        definition = definition.replace('public.', '')
        idx.setdefault(t, []).append(definition)
    snap['indexes'] = {t: sorted(v) for t, v in sorted(idx.items())}

    snap['migrations'] = sorted(f"{a}.{n}" for a, n in q("SELECT app, name FROM django_migrations"))

    # RBAC configuration
    from skytron_api.models import UserRoleType, RolePermissionConfig
    snap['rbac_roles'] = {
        r.code: {'display_name': r.display_name, 'is_builtin': r.is_builtin, 'is_active': r.is_active}
        for r in UserRoleType.objects.all().order_by('code')
    }
    snap['rbac_permissions'] = {
        f"{p.role.code}|{p.module}": {
            'can_view': p.can_view, 'can_create': p.can_create, 'can_update': p.can_update,
            'can_delete': p.can_delete, 'can_filter': p.can_filter,
            'show_in_menu': p.show_in_menu, 'data_scope': p.data_scope,
        }
        for p in RolePermissionConfig.objects.select_related('role').order_by('role__code', 'module')
    }
    return snap


def diff_sets(label, ref, cur, out):
    missing, extra = sorted(set(ref) - set(cur)), sorted(set(cur) - set(ref))
    for m in missing:
        out.append(f"  MISSING on this DB  {label}: {m}")
    for e in extra:
        out.append(f"  EXTRA   on this DB  {label}: {e}")


def compare(ref, cur):
    sections = []

    out = []
    diff_sets('extension', ref['extensions'], cur['extensions'], out)
    sections.append(('Extensions', out))

    out = []
    diff_sets('table', ref['tables'], cur['tables'], out)
    for t in sorted(set(ref['tables']) & set(cur['tables'])):
        rc, cc = ref['tables'][t], cur['tables'][t]
        diff_sets(f'column {t}.', rc, cc, out)
        for col in sorted(set(rc) & set(cc)):
            if rc[col] != cc[col]:
                out.append(f"  DIFFERENT column {t}.{col}: dev=[{rc[col]}]  this=[{cc[col]}]")
    sections.append(('Tables and columns', out))

    for key, title in (('constraints', 'Constraints (PK/UNIQUE/FK/CHECK)'), ('indexes', 'Indexes')):
        out = []
        for t in sorted(set(ref[key]) | set(cur[key])):
            if t not in ref['tables'] or t not in cur['tables']:
                continue   # already reported as a missing/extra table
            diff_sets(f'{key[:-1]} on {t}:', ref[key].get(t, []), cur[key].get(t, []), out)
        sections.append((title, out))

    out = []
    diff_sets('migration', ref['migrations'], cur['migrations'], out)
    sections.append(('Applied migrations', out))

    out = []
    diff_sets('role', ref['rbac_roles'], cur['rbac_roles'], out)
    for code in sorted(set(ref['rbac_roles']) & set(cur['rbac_roles'])):
        if ref['rbac_roles'][code] != cur['rbac_roles'][code]:
            out.append(f"  DIFFERENT role {code}: dev={ref['rbac_roles'][code]}  this={cur['rbac_roles'][code]}")
    sections.append(('RBAC roles', out))

    out = []
    diff_sets('permission row (role|module)', ref['rbac_permissions'], cur['rbac_permissions'], out)
    for k in sorted(set(ref['rbac_permissions']) & set(cur['rbac_permissions'])):
        r, c = ref['rbac_permissions'][k], cur['rbac_permissions'][k]
        changed = {f: (r[f], c[f]) for f in r if r[f] != c.get(f)}
        if changed:
            out.append(f"  DIFFERENT {k}: " + ', '.join(f"{f} dev={a} this={b}" for f, (a, b) in changed.items()))
    sections.append(('RBAC permissions', out))

    print(f"Reference: {len(ref['tables'])} tables, {len(ref['migrations'])} migrations, "
          f"{len(ref['rbac_roles'])} roles, {len(ref['rbac_permissions'])} permission rows")
    print(f"This DB:   {len(cur['tables'])} tables, {len(cur['migrations'])} migrations, "
          f"{len(cur['rbac_roles'])} roles, {len(cur['rbac_permissions'])} permission rows")
    total = 0
    for title, lines in sections:
        total += len(lines)
        print(f"\n== {title}: {'OK - identical' if not lines else f'{len(lines)} difference(s)'}")
        for line in lines[:60]:
            print(line)
        if len(lines) > 60:
            print(f"  ... and {len(lines) - 60} more")
    print(f"\nRESULT: {'IDENTICAL' if total == 0 else f'{total} DIFFERENCE(S)'}")


current = snapshot()
if MODE == 'export':
    with open(REF, 'w') as f:
        json.dump(current, f, indent=1, sort_keys=True)
    print(f"Reference written to {REF}: {len(current['tables'])} tables, "
          f"{len(current['rbac_permissions'])} RBAC permission rows")
else:
    with open(REF) as f:
        compare(json.load(f), current)
