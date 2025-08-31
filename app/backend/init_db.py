import mysql.connector
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    # Get database connection for initialization
    try:
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            # Railway production
            host = os.environ.get("MYSQLHOST")
            user = os.environ.get("MYSQLUSER")
            password = os.environ.get("MYSQLPASSWORD")
            database = os.environ.get("MYSQLDATABASE")
            port = int(os.environ.get("MYSQLPORT", 3306))
        else:
            # Local development
            host = "127.0.0.1"
            user = "root"
            password = "theo"
            database = "theo_eat"
            port = 3306
        
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            auth_plugin="mysql_native_password",
            autocommit=False,  # Manual control for initialization
            charset='utf8mb4'
        )
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def read_sql_file():
    # Read the theo_eats.sql file
    try:
        # From backend folder, go up one level, then into database folder
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'theo_eats.sql')
        
        if not os.path.exists(sql_file_path):
            logger.error(f"SQL file not found at: {sql_file_path}")
            return None
            
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            return file.read()
            
    except Exception as e:
        logger.error(f"Error reading SQL file: {e}")
        return None

def check_tables_exist(cursor):
    # Check if tables already exist
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['food_items', 'orders', 'order_items', 'order_tracking']
    existing_tables = [table for table in required_tables if table in tables]
    
    logger.info(f"Existing tables: {existing_tables}")
    return len(existing_tables) == len(required_tables)

def execute_sql_statements(cursor, sql_content):
    # Execute SQL statements from the file
    try:
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement.upper().startswith(('CREATE', 'INSERT', 'ALTER', 'DROP')):
                try:
                    cursor.execute(statement)
                    logger.info(f"Executed: {statement[:50]}...")
                except mysql.connector.Error as e:
                    # Log but continue - some statements might already exist
                    logger.warning(f"Statement failed (might be normal): {e}")
                    
    except Exception as e:
        logger.error(f"Error executing SQL statements: {e}")
        raise

def initialize_database():
    # Main initialization function
    conn = None
    cursor = None
    
    try:
        logger.info("Starting database initialization...")
        
        # Get connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if database is already initialized
        if check_tables_exist(cursor):
            logger.info("Database already initialized. Skipping...")
            return True
            
        # Read SQL file
        sql_content = read_sql_file()
        if not sql_content:
            logger.error("Failed to read SQL file")
            return False
            
        # Execute SQL statements
        execute_sql_statements(cursor, sql_content)
        
        # Commit all changes
        conn.commit()
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database initialization failed: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def verify_initialization():
    # Verify that initialization was successful
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check table counts
        tables_info = {}
        required_tables = ['food_items', 'orders', 'order_items', 'order_tracking']
        
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            tables_info[table] = count
            
        logger.info(f"Table verification: {tables_info}")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    success = initialize_database()
    if success:
        verify_initialization()
    else:
        logger.error("Database initialization failed!")
