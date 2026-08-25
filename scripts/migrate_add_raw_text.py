import sqlite3
import os

db_path = "recovery.db"

if os.path.exists(db_path):
    print(f"Connecting to database {db_path} to check for raw_failure_text column...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN raw_failure_text TEXT;")
        conn.commit()
        print("Successfully added raw_failure_text column to transactions table!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column raw_failure_text already exists. No migration needed.")
        else:
            print(f"Migration error: {e}")
    finally:
        conn.close()
else:
    print(f"Database {db_path} not found. Column will be created on next DB initialization.")
