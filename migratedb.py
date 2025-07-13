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
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', '135.235.166.209'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'dbadmin'),
            password=os.getenv('DB_PASSWORD', 'lask1028zmnx'),
            database=db_name
        )
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to {db_name}: {e}")
        return None

def get_all_tables(conn):
    """Get all table names from the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
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

def disable_triggers(conn, table_name):
    """Disable triggers for faster insertion"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {table_name} DISABLE TRIGGER ALL")
        conn.commit()
        cursor.close()
    except Exception as e:
        logging.warning(f"Could not disable triggers for {table_name}: {e}")

def enable_triggers(conn, table_name):
    """Re-enable triggers"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {table_name} ENABLE TRIGGER ALL")
        conn.commit()
        cursor.close()
    except Exception as e:
        logging.warning(f"Could not enable triggers for {table_name}: {e}")

def copy_table_data(old_conn, new_conn, table_name):
    """Copy data from old table to new table"""
    try:
        # Get column info
        columns = get_table_columns(old_conn, table_name)
        if not columns:
            logging.warning(f"No columns found for table {table_name}")
            return False
        
        column_names = [col[0] for col in columns]
        column_list = ', '.join(column_names)
        placeholders = ', '.join(['%s'] * len(column_names))
        
        # Check if table exists in new database
        new_cursor = new_conn.cursor()
        new_cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
        """, (table_name,))
        
        if not new_cursor.fetchone()[0]:
            logging.warning(f"Table {table_name} does not exist in new database, skipping...")
            new_cursor.close()
            return False
        
        new_cursor.close()
        
        # Get row count
        old_cursor = old_conn.cursor()
        old_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = old_cursor.fetchone()[0]
        
        if total_rows == 0:
            logging.info(f"Table {table_name} is empty, skipping...")
            old_cursor.close()
            return True
        
        logging.info(f"Copying {total_rows} rows from {table_name}...")
        
        # Disable triggers for faster insertion
        disable_triggers(new_conn, table_name)
        
        # Clear existing data in new table
        new_cursor = new_conn.cursor()
        new_cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
        new_conn.commit()
        
        # Copy data in batches
        batch_size = 1000
        offset = 0
        copied_rows = 0
        
        while offset < total_rows:
            # Fetch batch from old database
            old_cursor.execute(f"""
                SELECT {column_list} 
                FROM {table_name} 
                ORDER BY (SELECT NULL)
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            rows = old_cursor.fetchall()
            if not rows:
                break
            
            # Insert batch into new database
            insert_query = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
            new_cursor.executemany(insert_query, rows)
            new_conn.commit()
            
            copied_rows += len(rows)
            offset += batch_size
            
            if copied_rows % 5000 == 0:
                logging.info(f"Copied {copied_rows}/{total_rows} rows for {table_name}")
        
        # Re-enable triggers
        enable_triggers(new_conn, table_name)
        
        old_cursor.close()
        new_cursor.close()
        
        logging.info(f"Successfully copied {copied_rows} rows to {table_name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to copy data for table {table_name}: {e}")
        # Try to re-enable triggers in case of error
        try:
            enable_triggers(new_conn, table_name)
        except:
            pass
        return False

def main():
    """Main migration function"""
    # Load environment variables
    old_db_name = os.getenv('OLD_DB_NAME', 'skytrondbnew2')
    new_db_name = os.getenv('DB_NAME', 'skytrondb_main')
    
    logging.info(f"Starting migration from {old_db_name} to {new_db_name}")
    
    # Connect to databases
    old_conn = get_db_connection(old_db_name)
    new_conn = get_db_connection(new_db_name)
    
    if not old_conn or not new_conn:
        logging.error("Failed to establish database connections")
        return
    
    try:
        # Get all tables from old database
        tables = get_all_tables(old_conn)
        logging.info(f"Found {len(tables)} tables to migrate")
        
        successful_tables = []
        failed_tables = []
        
        for i, table in enumerate(tables, 1):
            logging.info(f"Processing table {i}/{len(tables)}: {table}")
            
            if copy_table_data(old_conn, new_conn, table):
                successful_tables.append(table)
            else:
                failed_tables.append(table)
        
        # Summary
        logging.info("="*50)
        logging.info("MIGRATION SUMMARY")
        logging.info("="*50)
        logging.info(f"Total tables: {len(tables)}")
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
        
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    main()
