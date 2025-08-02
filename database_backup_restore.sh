#!/bin/bash

# Database Backup and Restore Script
# Based on your current database configuration

# Current Database Configuration
DB_NAME="skytrondb_main"
DB_USER="dbadmin"
DB_PASSWORD="lask1028zmnx"
DB_HOST="135.235.166.209"
DB_PORT="5432"

# New Server Configuration (Update these values for your new server)
NEW_DB_HOST="YOUR_NEW_SERVER_IP"
NEW_DB_USER="dbadmin"
NEW_DB_PASSWORD="YOUR_NEW_PASSWORD"
NEW_DB_NAME="skytrondb_main"

echo "=== PostgreSQL Database Backup and Restore Script ==="
echo ""

echo "STEP 1: Create backup of current database"
echo "========================================"
echo "Run this command on your current server or from a machine that can connect to it:"
echo ""
echo "pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f skytrondb_backup_$(date +%Y%m%d_%H%M%S).sql"
echo ""
echo "Or with verbose output and custom format (recommended):"
echo "pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -Fc -v -f skytrondb_backup_$(date +%Y%m%d_%H%M%S).dump"
echo ""

echo "STEP 2: Transfer backup file to new server"
echo "=========================================="
echo "Use scp or any file transfer method to move the backup file to your new server"
echo "Example:"
echo "scp skytrondb_backup_*.sql username@new_server_ip:/path/to/backup/"
echo ""

echo "STEP 3: Commands to run on NEW server"
echo "====================================="
echo ""

echo "3a. Connect to PostgreSQL as superuser (usually postgres):"
echo "sudo -u postgres psql"
echo ""

echo "3b. Drop existing database (CAREFUL - this will delete all data!):"
echo "DROP DATABASE IF EXISTS $NEW_DB_NAME;"
echo ""

echo "3c. Create new database:"
echo "CREATE DATABASE $NEW_DB_NAME OWNER $NEW_DB_USER;"
echo ""

echo "3d. Grant privileges:"
echo "GRANT ALL PRIVILEGES ON DATABASE $NEW_DB_NAME TO $NEW_DB_USER;"
echo ""

echo "3e. Exit psql:"
echo "\\q"
echo ""

echo "STEP 4: Restore the database"
echo "============================"
echo "If you used regular SQL format (.sql):"
echo "psql -h $NEW_DB_HOST -p $DB_PORT -U $NEW_DB_USER -d $NEW_DB_NAME -f skytrondb_backup_YYYYMMDD_HHMMSS.sql"
echo ""
echo "If you used custom format (.dump):"
echo "pg_restore -h $NEW_DB_HOST -p $DB_PORT -U $NEW_DB_USER -d $NEW_DB_NAME -v skytrondb_backup_YYYYMMDD_HHMMSS.dump"
echo ""

echo "STEP 5: Verify the restore"
echo "=========================="
echo "Connect to the new database and check:"
echo "psql -h $NEW_DB_HOST -p $DB_PORT -U $NEW_DB_USER -d $NEW_DB_NAME"
echo ""
echo "Then run some verification queries:"
echo "\\dt  -- List all tables"
echo "\\du  -- List all users"
echo "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
echo ""

echo "=== IMPORTANT NOTES ==="
echo "1. Make sure PostgreSQL client tools are installed (pg_dump, pg_restore, psql)"
echo "2. Update the NEW_DB_HOST, NEW_DB_PASSWORD variables above before using"
echo "3. Ensure network connectivity between servers"
echo "4. The user $NEW_DB_USER must exist on the new server with appropriate permissions"
echo "5. Always test the backup/restore process on a non-production environment first"
echo ""

echo "=== QUICK COMMANDS SUMMARY ==="
echo ""
echo "# 1. Backup (run from current server or client machine):"
echo "export PGPASSWORD='$DB_PASSWORD'"
echo "pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -Fc -v -f skytrondb_backup_\$(date +%Y%m%d_%H%M%S).dump"
echo ""
echo "# 2. On new server - drop and recreate database:"
echo "sudo -u postgres psql -c \"DROP DATABASE IF EXISTS $NEW_DB_NAME;\""
echo "sudo -u postgres psql -c \"CREATE DATABASE $NEW_DB_NAME OWNER $NEW_DB_USER;\""
echo ""
echo "# 3. Restore (update host and credentials for new server):"
echo "export PGPASSWORD='YOUR_NEW_PASSWORD'"
echo "pg_restore -h YOUR_NEW_SERVER_IP -p $DB_PORT -U $NEW_DB_USER -d $NEW_DB_NAME -v skytrondb_backup_YYYYMMDD_HHMMSS.dump"
