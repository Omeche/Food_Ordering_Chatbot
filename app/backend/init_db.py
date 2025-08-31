import mysql.connector
import os
import logging
from urllib.parse import urlparse
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    # Get database connection for initialization
    try:
        # Check for Railway's MYSQL_URL 
        mysql_url = os.environ.get("MYSQL_URL")
        
        if mysql_url:
            # Parse Railway's MYSQL_URL format: mysql://user:password@host:port/database
            parsed = urlparse(mysql_url)
            
            host = parsed.hostname
            user = parsed.username
            password = parsed.password
            database = parsed.path[1:]  # Remove leading slash
            port = parsed.port or 3306
            
            logger.info(f"Using Railway MySQL URL connection to {host}:{port}")
            
        elif os.environ.get("RAILWAY_ENVIRONMENT"):
            # Fallback to individual variables if they exist
            host = os.environ.get("MYSQLHOST")
            user = os.environ.get("MYSQLUSER")
            password = os.environ.get("MYSQLPASSWORD")
            database = os.environ.get("MYSQLDATABASE")
            port_str = os.environ.get("MYSQLPORT", "3306")
            
            # Validate all environment variables are present
            if not all([host, user, password, database]):
                missing_vars = [var for var, val in [
                    ("MYSQLHOST", host), ("MYSQLUSER", user), 
                    ("MYSQLPASSWORD", password), ("MYSQLDATABASE", database)
                ] if not val]
                raise ValueError(f"Missing environment variables: {missing_vars}")
            
            port = int(port_str)
            logger.info(f"Using Railway individual variables to {host}:{port}")
        else:
            # Local development
            host = "127.0.0.1"
            user = "root"
            password = "theo"
            database = "theo_eat"
            port = 3306
            logger.info(f"Using local development connection to {host}:{port}")
        
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
    # Read the theo_eats.sql file and clean it for Railway
    try:
        current_dir = os.path.dirname(__file__)
        logger.info(f"Current directory: {current_dir}")
        
        # Based on logs
        possible_paths = [
            '/app/database/theo_eat.sql',
            os.path.join(current_dir, '..', '..', 'database', 'theo_eat.sql'),
        ]
        
        sql_content = None
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found SQL file at: {path}")
                with open(path, 'r', encoding='utf-8') as file:
                    sql_content = file.read()
                break
        
        if not sql_content:
            logger.error("SQL file not found")
            return None
            
        # Clean the SQL content for Railway compatibility
        cleaned_content = clean_sql_for_railway(sql_content)
        return cleaned_content
            
    except Exception as e:
        logger.error(f"Error reading SQL file: {e}")
        return None

def clean_sql_for_railway(sql_content):
    # Clean SQL content to be Railway-compatible
    # Remove problematic statements
    sql_content = re.sub(r'CREATE DATABASE.*?;', '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    sql_content = re.sub(r'USE\s+\w+\s*;', '', sql_content, flags=re.IGNORECASE)
    
    # Fix collation issues
    sql_content = sql_content.replace('utf8mb4_0900_ai_ci', 'utf8mb4_unicode_ci')
    
    # Ensure proper spacing around INSERT statements
    sql_content = re.sub(r'(\))(\s*)(CREATE)', r'\1;\2\3', sql_content)
    
    return sql_content

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
        # Handle DELIMITER statements for stored procedures/functions
        current_delimiter = ';'
        statements = []
        current_statement = ""
        
        lines = sql_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                i += 1
                continue
                
            # Handle DELIMITER changes
            if line.upper().startswith('DELIMITER'):
                if current_statement.strip():
                    statements.append(current_statement.strip())
                    current_statement = ""
                current_delimiter = line.split()[-1]
                i += 1
                continue
            
            # Add line to current statement
            current_statement += line + '\n'
            
            # Check if statement is complete
            if line.endswith(current_delimiter):
                # Remove the delimiter from the statement
                if current_delimiter != ';':
                    current_statement = current_statement.replace(current_delimiter, '').strip()
                statements.append(current_statement.strip())
                current_statement = ""
                
                # Reset delimiter after procedure/function
                if current_delimiter != ';':
                    current_delimiter = ';'
            
            i += 1
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        # Execute each statement
        for statement in statements:
            if statement and not statement.startswith('--'):
                try:
                    # Clean the statement
                    statement = statement.replace(';;', ';').strip()
                    if statement.endswith(';'):
                        statement = statement[:-1]
                    
                    cursor.execute(statement)
                    logger.info(f"Executed: {statement[:60]}...")
                    
                except mysql.connector.Error as e:
                    # Log warnings for expected failures 
                    if "doesn't exist" in str(e) or "Unknown" in str(e):
                        logger.warning(f"Statement failed (might be normal): {e}")
                    else:
                        logger.error(f"Statement failed: {e}")
                        logger.error(f"Failed statement: {statement[:200]}...")
                        
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
            
        logger.info("Executing database schema and procedures...")
        
        # Execute SQL statements
        execute_sql_statements(cursor, sql_content)
        
        # Commit all changes
        conn.commit()
        logger.info("Database initialization completed successfully!")
        
        # Verify initialization
        verify_initialization()
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
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                tables_info[table] = count
            except mysql.connector.Error as e:
                tables_info[table] = f"Error: {e}"
                
        logger.info(f"Table verification: {tables_info}")
        
        # Check if stored procedures exist
        cursor.execute("SHOW PROCEDURE STATUS WHERE Db = DATABASE()")
        procedures = [row[1] for row in cursor.fetchall()]
        logger.info(f"Created procedures: {procedures}")
        
        # Check if functions exist
        cursor.execute("SHOW FUNCTION STATUS WHERE Db = DATABASE()")
        functions = [row[1] for row in cursor.fetchall()]
        logger.info(f"Created functions: {functions}")
        
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
        logger.info("Database setup completed successfully!")
    else:
        logger.error("Database initialization failed!")
