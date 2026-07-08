#!/bin/bash

# Database flush and reset script for Skytrack Backend
# This script will:
# 1. Flush all data from database tables
# 2. Reset all ID sequences to 0
# 3. Insert specific user data

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting database flush and reset process...${NC}"

# Get database connection details from environment variables or use defaults
DB_NAME=${DB_NAME:-"skytrack_db"}
DB_USER=${DB_USER:-"postgres"}
DB_PASSWORD=${DB_PASSWORD:-"password"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}

# Check if environment variables are set
if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: Database environment variables not set!${NC}"
    echo "Please set DB_NAME, DB_USER, and DB_PASSWORD environment variables"
    echo "Example:"
    echo "export DB_NAME=your_database_name"
    echo "export DB_USER=your_username"
    echo "export DB_PASSWORD=your_password"
    exit 1
fi

# Function to execute SQL commands
execute_sql() {
    local sql_command="$1"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql_command"
}

# Function to check if database connection is working
check_db_connection() {
    echo -e "${YELLOW}Checking database connection...${NC}"
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}Database connection successful!${NC}"
        return 0
    else
        echo -e "${RED}Failed to connect to database!${NC}"
        echo "Please check your database credentials and ensure PostgreSQL is running"
        return 1
    fi
}

# Function to get all table names from skytron_api app
get_table_names() {
    echo -e "${YELLOW}Getting table names...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'skytron_api_%'
        ORDER BY tablename;
    " | sed 's/^[ \t]*//;s/[ \t]*$//' | grep -v '^$'
}

# Function to truncate all tables and reset sequences
truncate_tables() {
    echo -e "${YELLOW}Truncating all tables and resetting sequences...${NC}"
    
    local tables=$(get_table_names)
    
    if [ -z "$tables" ]; then
        echo -e "${RED}No tables found to truncate!${NC}"
        return 1
    fi
    
    # Disable foreign key checks temporarily
    execute_sql "SET session_replication_role = replica;"
    
    # Truncate each table and reset sequences
    for table in $tables; do
        echo "Truncating table: $table"
        execute_sql "TRUNCATE TABLE $table RESTART IDENTITY CASCADE;"
        
        # Reset sequence if it exists
        sequence_name="${table}_id_seq"
        sequence_check=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT 1 FROM pg_class WHERE relname = '$sequence_name' AND relkind = 'S';
        " | sed 's/^[ \t]*//;s/[ \t]*$//' | grep -v '^$')
        
        if [ ! -z "$sequence_check" ]; then
            echo "Resetting sequence: $sequence_name"
            execute_sql "ALTER SEQUENCE $sequence_name RESTART WITH 1;"
        fi
    done
    
    # Re-enable foreign key checks
    execute_sql "SET session_replication_role = DEFAULT;"
    
    echo -e "${GREEN}All tables truncated and sequences reset!${NC}"
}

# Function to insert user data
insert_user_data() {
    echo -e "${YELLOW}Inserting user data...${NC}"
    
    local sql_insert="
    INSERT INTO skytron_api_user (
        id,
        is_superuser,
        name,
        email,
        mobile,
        role,
        usertype,
        createdby,
        date_joined,
        created,
        \"Access\",
        password,
        is_active,
        is_staff,
        address,
        address_pin,
        \"address_State\",
        dob,
        status,
        last_login,
        last_activity,
        login
    ) VALUES
    (1, true, 'ankur superadmin', 'a65471280@gmail.com', '8638760290', 'superadmin', 'main', '1', '2024-08-14 20:33:26.815802+05:30', '2024-08-14 20:33:27.051642+05:30', '[]', 'pbkdf2_sha256\$1000000\$KxKAgjyC5mOUu5uHmvsTQW\$IzDO6ZhZdCW8i6RVvXTnu6tL195ZHxKz4gqXj04K0hA=', true, true, NULL, NULL, NULL, '2024-08-11', 'active', '2025-07-12 09:48:44.897242+05:30', '2025-07-12 09:48:44.897242+05:30', true),
    (2, true, 'superadmin sujal', 'b.sujal@gmail.com', '9773300556', 'superadmin', 'main', '1', '2024-08-11 12:33:26.141273+05:30', '2024-08-11 12:33:26.381213+05:30', '[]', 'pbkdf2_sha256\$600000\$IGBPyT9BwFAw77PzTyS2Vz\$67PEps8b2VV57lW4ALl56Mz6bLU4Dv6m2Nvy1OADc7g=', true, true, NULL, NULL, NULL, '2024-08-11', 'pwreset', '2025-06-25 12:19:58.15282+05:30', '2025-06-25 12:19:58.15282+05:30', true),
    (3, true, 'kishalaySpperadmin', 'kishalaychakraborty1@gmail.com', '9401633421', 'superadmin', 'main', '1', '2024-08-19 08:02:18.079454+05:30', '2024-08-19 08:02:18.308701+05:30', '[]', 'pbkdf2_sha256\$600000\$64aissMbwogjm6LIwPUv3c\$TweWpS10MI9lp6kWNcWicM6EQJkYVmClck9pfITRFfs=', true, true, NULL, NULL, NULL, '2007-07-01', 'active', '2025-07-03 14:09:13.026577+05:30', '2025-07-03 14:09:13.026577+05:30', true);
    "
    
    if execute_sql "$sql_insert"; then
        echo -e "${GREEN}User data inserted successfully!${NC}"
        
        # Update the sequence to start from 4 for the next insert
        execute_sql "SELECT setval('skytron_api_user_id_seq', 3, true);"
        echo -e "${GREEN}User ID sequence updated to start from 4 for next insert${NC}"
    else
        echo -e "${RED}Failed to insert user data!${NC}"
        return 1
    fi
}

# Function to verify the inserted data
verify_data() {
    echo -e "${YELLOW}Verifying inserted data...${NC}"
    
    local count=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM skytron_api_user;
    " | sed 's/^[ \t]*//;s/[ \t]*$//')
    
    if [ "$count" = "3" ]; then
        echo -e "${GREEN}Verification successful: 3 users found in database${NC}"
        
        # Show the inserted users
        echo -e "${YELLOW}Inserted users:${NC}"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT id, name, email, mobile, role, status 
            FROM skytron_api_user 
            ORDER BY id;
        "
    else
        echo -e "${RED}Verification failed: Expected 3 users, found $count${NC}"
        return 1
    fi
}

# Function to create a backup before proceeding
create_backup() {
    echo -e "${YELLOW}Creating database backup before proceeding...${NC}"
    local backup_filename="skytrack_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$backup_filename" 2>/dev/null; then
        echo -e "${GREEN}Backup created: $backup_filename${NC}"
    else
        echo -e "${YELLOW}Warning: Could not create backup, but continuing...${NC}"
    fi
}

# Main execution
main() {
    echo -e "${YELLOW}=== Skytrack Database Reset Script ===${NC}"
    echo "This script will:"
    echo "1. Create a backup of current database"
    echo "2. Flush all data from all tables"
    echo "3. Reset all ID sequences to start from 1"
    echo "4. Insert 3 specific superadmin users"
    echo
    
    # Ask for confirmation
    read -p "Are you sure you want to proceed? This will DELETE ALL DATA! (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        echo -e "${YELLOW}Operation cancelled.${NC}"
        exit 0
    fi
    
    # Check database connection
    if ! check_db_connection; then
        exit 1
    fi
    
    # Create backup
    create_backup
    
    # Truncate tables and reset sequences
    if ! truncate_tables; then
        echo -e "${RED}Failed to truncate tables!${NC}"
        exit 1
    fi
    
    # Insert user data
    if ! insert_user_data; then
        echo -e "${RED}Failed to insert user data!${NC}"
        exit 1
    fi
    
    # Verify the data
    if ! verify_data; then
        echo -e "${RED}Data verification failed!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}=== Database reset completed successfully! ===${NC}"
    echo -e "${GREEN}All tables have been flushed and 3 superadmin users have been inserted.${NC}"
}

# Run the main function
main "$@"
