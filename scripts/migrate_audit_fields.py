import sqlite3
import os

db_path = "recovery.db"

if os.path.exists(db_path):
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Columns to add
    new_columns = [
        ("diagnosis_source", "TEXT"),
        ("diagnosis_reasoning", "TEXT"),
        ("predictor_status", "TEXT"),
        ("policy_override_reason", "TEXT"),
        ("rules_evaluated", "TEXT"), # JSON text
        ("approved_action", "TEXT"),
        ("execution_result", "TEXT"),
        ("recovery_amount", "REAL"),
        ("net_recovery", "REAL"),
        ("fallback_status", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE recovery_attempts ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} ({col_type})")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                raise e
                
    conn.commit()
    conn.close()
    print("Migration successful.")
else:
    print(f"Database {db_path} does not exist yet. It will be created with correct columns on startup.")
