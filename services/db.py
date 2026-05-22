import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'procedure.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # ProcedureState table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ProcedureState (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            species TEXT NOT NULL,
            weight REAL NOT NULL,
            start_time TEXT NOT NULL
        )
    ''')
    # ProcedureEvent table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ProcedureEvent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            procedure_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (procedure_id) REFERENCES ProcedureState(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def start_procedure(patient_name: str, species: str, weight: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    start_time = datetime.utcnow().isoformat()
    cursor.execute(
        'INSERT INTO ProcedureState (patient_name, species, weight, start_time) VALUES (?,?,?,?)',
        (patient_name, species, weight, start_time)
    )
    proc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return proc_id

def add_event(procedure_id: int, event_type: str, details: dict):
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    details_json = json.dumps(details, ensure_ascii=False)
    cursor.execute(
        'INSERT INTO ProcedureEvent (procedure_id, event_type, timestamp, details) VALUES (?,?,?,?)',
        (procedure_id, event_type, timestamp, details_json)
    )
    conn.commit()
    conn.close()

def get_events(procedure_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, event_type, timestamp, details FROM ProcedureEvent WHERE procedure_id = ? ORDER BY timestamp',
        (procedure_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        events.append({
            'id': row['id'],
            'event_type': row['event_type'],
            'timestamp': row['timestamp'],
            'details': json.loads(row['details']) if row['details'] else None
        })
    return events

# Initialize DB on import
init_db()
