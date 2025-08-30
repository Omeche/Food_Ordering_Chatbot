import mysql.connector
import os

# Connect using Railway private endpoint
conn = mysql.connector.connect(
    host=os.environ["RAILWAY_PRIVATE_DOMAIN"],
    user=os.environ["MYSQLUSER"],
    password=os.environ["MYSQLPASSWORD"],
    database=os.environ["MYSQLDATABASE"],
    port=int(os.environ["MYSQLPORT"]),
    autocommit=True
)

cursor = conn.cursor()

sql_file_path = "theo_eat.sql"  # relative path inside container

with open(sql_file_path, "r", encoding="utf8") as f:
    sql_commands = f.read().split(";")

for command in sql_commands:
    command = command.strip()
    if command:
        cursor.execute(command)

print("Private Railway DB import completed successfully!")

cursor.close()
conn.close()
