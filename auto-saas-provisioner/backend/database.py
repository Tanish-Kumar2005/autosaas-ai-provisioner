import sqlite3
import pandas as pd

DB_NAME = "provisioner_state.db"

def init_db():
    """Initializes the SQLite database and creates necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Table-1: Tracks each overall CSV upload run session
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            filename TEXT,
            total_records INTEGER,
            status TEXT
        )
    ''')

    # Table-2: Tracks every individual user record and its current provisioning state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id TEXT,
            run_id TEXT,
            email TEXT,
            role TEXT,
            status TEXT,
            error TEXT,
            PRIMARY KEY (id, run_id)
        )
    ''')

    # Table-3: Audit logs table for full execution tracing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            details TEXT
        )
    ''')

    conn.commit()
    conn.close()


def save_parsed_csv(run_id, filename, records):
    """Saves the cleaned and deduplicated CSV rows into the database."""
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO runs (run_id, filename, total_records, status) VALUES (?, ?, ?, ?)",
        (run_id, filename, len(records), "pending")
    )

    for r in records:
        cursor.execute(
            "INSERT OR REPLACE INTO records (id, run_id, email, role, status, error) VALUES (?, ?, ?, ?, ?, ?)",
            (r["id"], run_id, r["email"], r["role"], r["status"], r.get("error", ""))
        )

    conn.commit()
    conn.close()


def get_pending_records(run_id):
    """Fetches records that have not successfully finished (crucial for TC4 batch retries)."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT * FROM records WHERE run_id = ? AND status != 'success'",
        conn,
        params=(run_id,) 
    )
    conn.close()
    return df.to_dict(orient="records")


def update_record_status(run_id, record_id, status, error=""):
    """Updates an individual user's status to 'success' or 'failed' during execution."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE records SET status = ?, error = ? WHERE run_id = ? AND id = ?",
        (status, error, run_id, record_id)
    )

    conn.commit()
    conn.close()


def update_run_status(run_id, status):
    """Updates the overall run status (pending, running, completed, failed)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE runs SET status = ? WHERE run_id = ?", (status, run_id))
    conn.commit()
    conn.close()


def log_audit_event(run_id, event_type, details):
    """Logs structured trace events for compliance and audit views."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (run_id, event_type, details) VALUES (?, ?, ?)",
        (run_id, event_type, details)
    )
    conn.commit()
    conn.close()