#!/bin/bash

DB_NAME="skytrondb_main"
DB_USER="dbadmin"
DB_PASSWORD="lask1028zmnx"

sudo -u postgres psql <<EOF

CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

\c $DB_NAME

GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
GRANT USAGE, CREATE ON SCHEMA public TO $DB_USER;

EOF
# ── GPS lite API performance index ─────────────────────────────────────────
# Supports DISTINCT ON (device_tag_id) ORDER BY device_tag_id, entry_time DESC
# for verified, active devices without a full GPSData table scan.
# CONCURRENTLY means no table lock — safe to run on live production.
# psql -U <db_user> -d <db_name> -c "
# CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gpsdata_lite_lookup
#     ON skytron_api_gpsdata (device_tag_id, entry_time DESC)
#     WHERE device_tag_id IS NOT NULL;
# "
