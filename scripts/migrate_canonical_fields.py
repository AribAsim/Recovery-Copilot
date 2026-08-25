import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "recovery.db")

print(f"Running sqlite3 schema migration on {db_path}...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Columns to add to transactions
tx_cols = [
    ("payment_id", "TEXT"),
    ("order_id", "TEXT"),
    ("currency", "TEXT DEFAULT 'INR'"),
    ("payment_method", "TEXT"),
    ("failure_source", "TEXT"),
    ("failure_step", "TEXT"),
    ("failure_reason", "TEXT"),
    ("gateway", "TEXT"),
    ("bank", "TEXT"),
    ("checkout_state", "TEXT")
]

for col_name, col_type in tx_cols:
    try:
        cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type};")
        print(f"Added column {col_name} to transactions table.")
    except sqlite3.OperationalError:
        print(f"Column {col_name} already exists in transactions table.")

# Columns to add to recovery_attempts
attempt_cols = [
    ("ai_recommendation", "TEXT"),
    ("ai_confidence", "REAL"),
    ("ai_predicted_probability", "REAL"),
    ("ai_reasoning", "TEXT"),
    ("policy_decision", "TEXT"),
    ("policy_block_reason", "TEXT"),
    ("expected_recovery_value", "REAL"),
    ("actual_outcome_amount", "REAL DEFAULT 0.0")
]

for col_name, col_type in attempt_cols:
    try:
        cursor.execute(f"ALTER TABLE recovery_attempts ADD COLUMN {col_name} {col_type};")
        print(f"Added column {col_name} to recovery_attempts table.")
    except sqlite3.OperationalError:
        print(f"Column {col_name} already exists in recovery_attempts table.")

conn.commit()
conn.close()
print("Migration completed.")
