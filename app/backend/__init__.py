import mysql.connector
import os

def initialize_database():
    """Initialize the database with the schema from theo_eats.sql"""
    try:
        # Read the SQL file
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'theo_eats.sql')
        
        with open(sql_file_path, 'r') as file:
            sql_content = file.read()
        
        # Connect to database
        if os.environ.get("RAILWAY_ENV") == "production":
            host = os.environ.get("MYSQLHOST")
            user = os.environ.get("MYSQLUSER")
            password = os.environ.get("MYSQLPASSWORD")
            database = os.environ.get("MYSQLDATABASE")
            port = int(os.environ.get("MYSQLPORT", 3306))
        else:
            host = "127.0.0.1"
            user = "root"
            password = "theo"
            database = "theo_eat"
            port = 3306
        
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            auth_plugin="mysql_native_password"
        )
        
        cursor = conn.cursor()
        
        # Execute SQL statements
        for statement in sql_content.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()
