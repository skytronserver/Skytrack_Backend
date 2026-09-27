"""
Run a SQL file in ONE transaction through Django's DB connection (no psql needed).

  Dry run (executes, then rolls back - nothing is changed):
    docker exec -e SQL=/tmp/nic_schema_fix.sql -e DRYRUN=1 <container> sh -c "python manage.py shell < /tmp/run_sql.py"
  Apply:
    docker exec -e SQL=/tmp/nic_schema_fix.sql <container> sh -c "python manage.py shell < /tmp/run_sql.py"

Any error rolls back every statement in the file.
"""
import os

from django.db import connection, transaction


class _DryRun(Exception):
    pass


path = os.environ['SQL']
dry = os.environ.get('DRYRUN') == '1'
sql = open(path).read()
try:
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(sql)
        if dry:
            raise _DryRun()
    print(f"OK: {path} applied (single transaction)")
except _DryRun:
    print(f"DRY RUN OK: every statement in {path} succeeded, then everything was rolled back")
