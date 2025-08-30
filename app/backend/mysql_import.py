import os
import mysql.connector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to your .sql file relative to the container root
SQL_FILE_PATH = "app/backend/theo_eat.sql"

# Get database connection details from Railway environment variables
DB_CONFIG = {
    "host": os.environ.get("RAILWAY_PRIVATE_DOMAIN") or os.environ.get("MYSQLHOST") or "127.0.0.1",
    "user": os.environ.get("MYSQLUSER") or "root",
    "password": os.environ.get("MYSQLPASSWORD") or "theo",
    "database": os.environ.get("MYSQLDATABASE") or "theo_eat",
    "auth_plugin": "mysql_native_password"
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.info(f"Connected to database {DB_CONFIG['database']} at {DB_CONFIG['host']}")
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def import_sql_file():
    if not os.path.exists(SQL_FILE_PATH):
        logger.error(f"SQL file not found at {SQL_FILE_PATH}")
        return

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        logger.info(f"Starting import of SQL file: {SQL_FILE_PATH}")
        with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
            sql_statements = f.read()

        # Split by semicolon to execute each statement
        statements = [stmt.strip() for stmt in sql_statements.split(";") if stmt.strip()]
        for stmt in statements:
            cursor.execute(stmt)
        conn.commit()
        logger.info(f"Successfully imported {len(statements)} SQL statements into {DB_CONFIG['database']}")
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error during SQL import: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting Railway private SQL import script")
    import_sql_file()
    logger.info("Import script finished")
