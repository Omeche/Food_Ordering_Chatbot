import os
import mysql.connector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to your SQL file relative to this script
SQL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'theo_eat.sql')

def get_connection():
    """
    Returns a MySQL connection.
    Uses Railway private endpoint if the environment variables exist.
    Falls back to local MySQL for development.
    """
    try:
        host = os.environ.get('MYSQLHOST', '127.0.0.1')
        user = os.environ.get('MYSQLUSER', 'root')
        password = os.environ.get('MYSQLPASSWORD', 'theo')
        database = os.environ.get('MYSQLDATABASE', 'theo_eat')
        port = int(os.environ.get('MYSQLPORT', 3306))

        logger.info(f"Connecting to database {database} at {host}:{port} as {user}")
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            auth_plugin="mysql_native_password",
            charset='utf8mb4',
            use_unicode=True
        )
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def import_sql_file(sql_file_path):
    """
    Reads the .sql file and executes all commands.
    """
    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file not found: {sql_file_path}")
        return

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read()

        # Split commands on semicolon for execution
        for command in sql_commands.split(';'):
            cmd = command.strip()
            if cmd:
                cursor.execute(cmd)
        
        conn.commit()
        logger.info(f"SQL file '{sql_file_path}' imported successfully.")
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error importing SQL file: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    import_sql_file(SQL_FILE_PATH)
