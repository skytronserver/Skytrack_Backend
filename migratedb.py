import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

def get_db_connection(db_name):
    """Create database connection with autocommit"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', '135.235.166.209'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'dbadmin'),
            password=os.getenv('DB_PASSWORD', 'lask1028zmnx'),
            database=db_name
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to {db_name}: {e}")
        return None

def get_skytron_tables(conn):
    """Get all skytron_api_* tables from the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name LIKE 'skytron_api_%'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Exception as e:
        logging.error(f"Failed to get table list: {e}")
        return []

def get_table_columns(conn, table_name):
    """Get column names for a table"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        return columns
    except Exception as e:
        logging.error(f"Failed to get columns for {table_name}: {e}")
        return []

def get_matching_columns(old_conn, new_conn, table_name):
    """Get columns that exist in both old and new databases with case-insensitive matching"""
    old_columns = {col[0].lower(): col[0] for col in get_table_columns(old_conn, table_name)}
    new_columns = {col[0].lower(): col[0] for col in get_table_columns(new_conn, table_name)}
    
    # Find matching columns (case insensitive)
    matching_columns = []
    for new_col_lower, new_col_name in new_columns.items():
        if new_col_lower in old_columns:
            matching_columns.append((old_columns[new_col_lower], new_col_name))
    
    return matching_columns

def clear_table_data(conn, table_name):
    """Clear table data using DELETE"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name}")
        deleted_count = cursor.rowcount
        cursor.close()
        if deleted_count > 0:
            logging.info(f"Cleared {deleted_count} existing rows from {table_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to clear table {table_name}: {e}")
        return False

def copy_table_data(old_conn, new_conn, table_name):
    """Copy data from old table to new table with column matching and error handling"""
    try:
        # Check if table exists in new database
        new_cursor = new_conn.cursor()
        new_cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
        """, (table_name,))
        
        table_exists = new_cursor.fetchone()[0]
        new_cursor.close()
        
        if not table_exists:
            logging.warning(f"Table {table_name} does not exist in new database, skipping...")
            return False
        
        # Get matching columns between old and new tables
        matching_columns = get_matching_columns(old_conn, new_conn, table_name)
        
        if not matching_columns:
            logging.warning(f"No matching columns found for table {table_name}")
            return False
        
        old_column_list = ', '.join([f'"{col[0]}"' for col in matching_columns])  # Quote column names
        new_column_list = ', '.join([f'"{col[1]}"' for col in matching_columns])  # Quote column names
        placeholders = ', '.join(['%s'] * len(matching_columns))
        
        logging.info(f"Matching columns for {table_name}: {len(matching_columns)}")
        
        # Get row count
        old_cursor = old_conn.cursor()
        old_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = old_cursor.fetchone()[0]
        
        if total_rows == 0:
            logging.info(f"Table {table_name} is empty, skipping...")
            old_cursor.close()
            return True
        
        logging.info(f"Copying {total_rows} rows from {table_name}...")
        
        # Clear existing data in new table (skip if it fails due to foreign keys)
        clear_success = clear_table_data(new_conn, table_name)
        if not clear_success:
            logging.warning(f"Could not clear table {table_name}, proceeding with insert...")
        
        # Copy data in batches
        batch_size = 100  # Smaller batch size for better error handling
        offset = 0
        copied_rows = 0
        
        while offset < total_rows:
            # Fetch batch from old database
            old_cursor.execute(f"""
                SELECT {old_column_list} 
                FROM {table_name} 
                ORDER BY (SELECT NULL)
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            rows = old_cursor.fetchall()
            if not rows:
                break
            
            # Insert batch into new database
            new_cursor = new_conn.cursor()
            try:
                # Use ON CONFLICT DO NOTHING for tables with primary keys
                insert_query = f"""
                    INSERT INTO {table_name} ({new_column_list}) 
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """
                new_cursor.executemany(insert_query, rows)
                copied_rows += len(rows)
                logging.debug(f"Inserted batch of {len(rows)} rows into {table_name}")
            except Exception as e:
                logging.warning(f"Failed to insert batch into {table_name}: {e}")
                # Try individual inserts for this batch
                success_count = 0
                for row in rows:
                    try:
                        new_cursor.execute(insert_query, row)
                        success_count += 1
                    except Exception as row_error:
                        logging.debug(f"Failed to insert row in {table_name}: {row_error}")
                copied_rows += success_count
                logging.info(f"Inserted {success_count}/{len(rows)} rows individually")
            finally:
                new_cursor.close()
            
            offset += batch_size
            
            if copied_rows % 500 == 0:
                logging.info(f"Copied {copied_rows}/{total_rows} rows for {table_name}")
        
        old_cursor.close()
        
        logging.info(f"Successfully copied {copied_rows} rows to {table_name}")
        return copied_rows > 0
        
    except Exception as e:
        logging.error(f"Failed to copy data for table {table_name}: {e}")
        return False

def reset_sequences(conn, table_name):
    """Reset auto-increment sequences for the table"""
    try:
        cursor = conn.cursor()
        # Find sequences related to this table
        cursor.execute("""
            SELECT column_name, column_default
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_default LIKE 'nextval%%'
        """, (table_name,))
        
        sequences = cursor.fetchall()
        for column_name, column_default in sequences:
            if 'nextval' in column_default:
                # Extract sequence name more safely
                seq_parts = column_default.split("'")
                if len(seq_parts) >= 2:
                    seq_name = seq_parts[1]
                    cursor.execute(f"""
                        SELECT setval('{seq_name}', 
                            COALESCE((SELECT MAX("{column_name}") FROM {table_name}), 1), 
                            true)
                    """)
                    logging.info(f"Reset sequence {seq_name} for table {table_name}")
        
        cursor.close()
        return True
    except Exception as e:
        logging.warning(f"Could not reset sequences for {table_name}: {e}")
        return False

def main():
    """Main migration function"""
    old_db_name = os.getenv('OLD_DB_NAME', 'skytrondbnew2')
    new_db_name = os.getenv('DB_NAME', 'skytrondb_main')
    
    logging.info(f"Starting migration from {old_db_name} to {new_db_name}")
    logging.info("Focusing on skytron_api_* tables only")
    
    # Connect to databases
    old_conn = get_db_connection(old_db_name)
    new_conn = get_db_connection(new_db_name)
    
    if not old_conn or not new_conn:
        logging.error("Failed to establish database connections")
        return
    
    try:
        # Get all skytron_api tables from both databases
        old_tables = get_skytron_tables(old_conn)
        new_tables = get_skytron_tables(new_conn)
        
        # Only process tables that exist in both databases
        common_tables = [table for table in old_tables if table in new_tables]
        
        logging.info(f"Found {len(old_tables)} tables in old database")
        logging.info(f"Found {len(new_tables)} tables in new database")
        logging.info(f"Common tables to migrate: {len(common_tables)}")
        
        if not common_tables:
            logging.warning("No common skytron_api_* tables found!")
            return
        
        successful_tables = []
        failed_tables = []
        
        # Define processing order to handle foreign key dependencies
        # Process tables with no foreign key dependencies first
        order_1_tables = [
            'skytron_api_settings_state',
            'skytron_api_settings_district', 
            'skytron_api_settings_vehiclecategory',
            'skytron_api_settings_firmware',
            'skytron_api_settings_hp_freq',
            'skytron_api_settings_ip',
            'skytron_api_settings_ip3',
            'skytron_api_captcha',
            'skytron_api_requestlog',
            'skytron_api_session'
        ]
        
        # Core entity tables that others depend on
        order_2_tables = [
            'skytron_api_user',
        ]
        
        # Secondary entity tables
        order_3_tables = [
            'skytron_api_manufacturer',
            'skytron_api_retailer', 
            'skytron_api_vehicleowner',
            'skytron_api_esimprovider',
            'skytron_api_stateadmin',
            'skytron_api_em_admin',
            'skytron_api_em_ex',
            'skytron_api_dto_rto'
        ]
        
        # Tables that depend on the above
        order_4_tables = [
            'skytron_api_devicemodel',
            'skytron_api_devicestock',
            'skytron_api_devicetag',
            'skytron_api_notice'
        ]
        
        # Process tables in dependency order
        all_ordered_tables = order_1_tables + order_2_tables + order_3_tables + order_4_tables
        remaining_tables = [table for table in common_tables if table not in all_ordered_tables]
        
        # Process each group
        for order_name, table_list in [
            ("Order 1 (Independent)", order_1_tables),
            ("Order 2 (Users)", order_2_tables), 
            ("Order 3 (Core Entities)", order_3_tables),
            ("Order 4 (Dependent)", order_4_tables),
            ("Remaining", remaining_tables)
        ]:
            logging.info(f"Processing {order_name} tables...")
            
            for table in table_list:
                if table in common_tables:
                    logging.info(f"Processing {table}...")
                    
                    if copy_table_data(old_conn, new_conn, table):
                        successful_tables.append(table)
                        reset_sequences(new_conn, table)
                    else:
                        failed_tables.append(table)
        
        # Summary
        logging.info("="*50)
        logging.info("MIGRATION SUMMARY")
        logging.info("="*50)
        logging.info(f"Total common skytron_api_* tables: {len(common_tables)}")
        logging.info(f"Successful: {len(successful_tables)}")
        logging.info(f"Failed: {len(failed_tables)}")
        
        if successful_tables:
            logging.info("Successful tables:")
            for table in successful_tables:
                logging.info(f"  ✓ {table}")
        
        if failed_tables:
            logging.info("Failed tables:")
            for table in failed_tables:
                logging.info(f"  ✗ {table}")
        
        # List tables that exist in old but not in new database
        missing_tables = [table for table in old_tables if table not in new_tables]
        if missing_tables:
            logging.info("Tables in old database but not in new:")
            for table in missing_tables:
                logging.info(f"  - {table}")
        
        if len(successful_tables) == len(common_tables):
            logging.info("🎉 All common skytron_api_* tables migrated successfully!")
        else:
            logging.info(f"Migration completed with {len(failed_tables)} failures")
        
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    main()