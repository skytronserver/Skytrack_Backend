#!/bin/bash

# Quick Database Migration Script
# Replace YOUR_NEW_SERVER_IP and YOUR_NEW_PASSWORD with actual values

echo "=== QUICK DATABASE MIGRATION COMMANDS ==="
echo ""

echo "1. BACKUP CURRENT DATABASE:"
echo "=========================="
echo "export PGPASSWORD='lask1028zmnx'"
echo "pg_dump -h 135.235.166.209 -p 5432 -U dbadmin -d skytrondb_main -Fc -v -f skytrondb_backup_\$(date +%Y%m%d_%H%M%S).dump"
echo ""

echo "2. TRANSFER FILE TO NEW SERVER:"
echo "==============================="
echo "# Use scp, rsync, or any file transfer method"
echo "# scp skytrondb_backup_*.dump user@new_server:/path/to/backup/"
echo ""

echo "3. ON NEW SERVER - DROP EXISTING DATABASE:"
echo "=========================================="
echo "sudo -u postgres psql -c \"DROP DATABASE IF EXISTS skytrondb_main;\""
echo "sudo -u postgres psql -c \"CREATE DATABASE skytrondb_main OWNER dbadmin;\""
echo ""

echo "4. RESTORE DATABASE ON NEW SERVER:"
echo "=================================="
echo "export PGPASSWORD='YOUR_NEW_PASSWORD'"
echo "pg_restore -h YOUR_NEW_SERVER_IP -p 5432 -U dbadmin -d skytrondb_main -v skytrondb_backup_YYYYMMDD_HHMMSS.dump"
echo ""

echo "5. VERIFY RESTORATION:"
echo "====================="
echo "psql -h YOUR_NEW_SERVER_IP -p 5432 -U dbadmin -d skytrondb_main -c \"\\dt\""
echo ""

echo "=== ALTERNATIVE: One-line backup command ==="
echo "PGPASSWORD='lask1028zmnx' pg_dump -h 135.235.166.209 -p 5432 -U dbadmin -d skytrondb_main --clean --no-owner --no-privileges -f skytrondb_full_backup.sql"
