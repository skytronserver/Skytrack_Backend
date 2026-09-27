"""
Make this database's RBAC configuration (UserRoleType + RolePermissionConfig) match
the reference exported from dev (dev_reference.json). Dev is the source of truth.

  Dry run (default - shows what would change, writes nothing):
    docker exec -e REF=/tmp/dev_reference.json <container> sh -c "python manage.py shell < /tmp/rbac_sync.py"
  Apply:
    docker exec -e REF=/tmp/dev_reference.json -e APPLY=1 <container> sh -c "python manage.py shell < /tmp/rbac_sync.py"
  Apply and also delete roles/permission rows that exist only here:
    ... -e APPLY=1 -e DELETE_EXTRA=1 ...

Everything runs in one transaction. Rows are saved one by one so the existing
post_save signal clears the RBAC cache; all touched roles are invalidated again
after commit so no stale permissions survive in Redis.
"""
import json
import os

from django.db import transaction

from skytron_api.models import RolePermissionConfig, User, UserRoleType
from skytron_api.rbac import invalidate_role_cache

REF = os.environ.get('REF', '/tmp/dev_reference.json')
APPLY = os.environ.get('APPLY') == '1'
DELETE_EXTRA = os.environ.get('DELETE_EXTRA') == '1'

ref = json.load(open(REF))
ref_roles, ref_perms = ref['rbac_roles'], ref['rbac_permissions']
PERM_FIELDS = ['can_view', 'can_create', 'can_update', 'can_delete', 'can_filter', 'show_in_menu', 'data_scope']

log, touched = [], set()


class _DryRun(Exception):
    pass


try:
    with transaction.atomic():
        # --- roles
        roles = {r.code: r for r in UserRoleType.objects.all()}
        for code, want in sorted(ref_roles.items()):
            r = roles.get(code)
            if r is None:
                r = UserRoleType(code=code)
                log.append(f"ADD role {code} ({want['display_name']})")
            else:
                changed = [f for f in ('display_name', 'description', 'is_builtin', 'is_active')
                           if f in want and (getattr(r, f) or '') != (want[f] or '') and getattr(r, f) != want[f]]
                if not changed:
                    continue
                log.append(f"UPDATE role {code}: " + ', '.join(f"{f} {getattr(r, f)!r}->{want[f]!r}" for f in changed))
            for f in ('display_name', 'description', 'is_builtin', 'is_active'):
                if f in want:
                    setattr(r, f, want[f])
            r.save()
            roles[code] = r
            touched.add(code)

        # --- permission rows
        existing = {f"{p.role.code}|{p.module}": p
                    for p in RolePermissionConfig.objects.select_related('role')}
        for key, want in sorted(ref_perms.items()):
            code, module = key.split('|', 1)
            p = existing.get(key)
            if p is None:
                p = RolePermissionConfig(role=roles[code], module=module)
                log.append(f"ADD perm {key}")
            else:
                changed = [f for f in PERM_FIELDS if getattr(p, f) != want[f]]
                if not changed:
                    continue
                log.append(f"UPDATE perm {key}: " + ', '.join(f"{f} {getattr(p, f)}->{want[f]}" for f in changed))
            for f in PERM_FIELDS:
                setattr(p, f, want[f])
            p.save()
            touched.add(code)

        # --- rows/roles that exist only on this database
        for key in sorted(set(existing) - set(ref_perms)):
            code = key.split('|', 1)[0]
            if DELETE_EXTRA:
                existing[key].delete(); touched.add(code)
                log.append(f"DELETE perm {key} (not on dev)")
            else:
                log.append(f"EXTRA perm {key} (only here - kept; use DELETE_EXTRA=1 to remove)")
        for code in sorted(set(roles) - set(ref_roles)):
            users = User.objects.filter(role=code).count()
            if DELETE_EXTRA and users == 0:
                RolePermissionConfig.objects.filter(role=roles[code]).delete()
                roles[code].delete(); touched.add(code)
                log.append(f"DELETE role {code} (not on dev, no users)")
            else:
                log.append(f"EXTRA role {code} (only here, {users} user(s) - kept)")

        if not APPLY:
            raise _DryRun()
    for code in touched:
        invalidate_role_cache(code)
    status = 'APPLIED'
except _DryRun:
    status = 'DRY RUN - nothing written'

counts = {}
for line in log:
    counts[line.split(' ')[0] + ' ' + line.split(' ')[1]] = counts.get(line.split(' ')[0] + ' ' + line.split(' ')[1], 0) + 1
print(f"{status}. Changes: " + (', '.join(f"{k}: {v}" for k, v in sorted(counts.items())) or 'none - already identical'))
for line in log[:80]:
    print('  ' + line)
if len(log) > 80:
    print(f"  ... and {len(log) - 80} more")
