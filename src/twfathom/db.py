import sqlite3
import json
from pathlib import Path
import os
from datetime import datetime

def get_db_path():
    if os.environ.get("TWFATHOM_DEV"):
        return Path("twfathom.db")
    db_dir = Path.home() / ".twfathom"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "twfathom.db"

def get_db_connection():
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. sources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,        -- 'mqtt', 'https', 'file'
        config TEXT NOT NULL,      -- JSON config
        interval INTEGER NOT NULL, -- polling interval in seconds
        data_type TEXT NOT NULL DEFAULT 'unknown',
        active INTEGER DEFAULT 1   -- 1: active, 0: paused
    );
    """)
    
    # 2. environment_data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS environment_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        temperature REAL,
        humidity REAL,
        pressure REAL,
        co2 REAL,
        soil_moisture REAL,
        FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
    );
    """)
    
    # 3. traffic_data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS traffic_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        rx_pps REAL,
        tx_pps REAL,
        rx_bps REAL,
        tx_bps REAL,
        FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
    );
    """)
    
    # Create indexes for time series queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_env_source_time ON environment_data (source_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_source_time ON traffic_data (source_id, timestamp);")
    
    # Check for legacy databases and migrate schema
    cursor.execute("PRAGMA table_info(sources);")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'data_type' not in columns:
        cursor.execute("ALTER TABLE sources ADD COLUMN data_type TEXT NOT NULL DEFAULT 'unknown';")
    if 'active' not in columns:
        cursor.execute("ALTER TABLE sources ADD COLUMN active INTEGER DEFAULT 1;")
        
    conn.commit()
    conn.close()

# Source CRUD
def add_source(name, type_, config_dict, interval, data_type="unknown"):
    conn = get_db_connection()
    cursor = conn.cursor()
    config_json = json.dumps(config_dict)
    cursor.execute("""
    INSERT INTO sources (name, type, config, interval, data_type, active)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (name, type_, config_json, interval, data_type))
    source_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return source_id

def get_sources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sources")
    rows = cursor.fetchall()
    sources = []
    for r in rows:
        d = dict(r)
        d['config'] = json.loads(d['config'])
        sources.append(d)
    conn.close()
    return sources

def get_source(source_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d['config'] = json.loads(d['config'])
        return d
    return None

def update_source(source_id, name, type_, config_dict, interval, data_type, active=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    config_json = json.dumps(config_dict)
    cursor.execute("""
    UPDATE sources
    SET name = ?, type = ?, config = ?, interval = ?, data_type = ?, active = ?
    WHERE id = ?
    """, (name, type_, config_json, interval, data_type, active, source_id))
    conn.commit()
    conn.close()

def delete_source(source_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()

# Data Insertion
def insert_environment_data(source_id, temperature=None, humidity=None, pressure=None, co2=None, soil_moisture=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO environment_data (source_id, timestamp, temperature, humidity, pressure, co2, soil_moisture)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (source_id, timestamp, temperature, humidity, pressure, co2, soil_moisture))
    conn.commit()
    conn.close()

def insert_traffic_data(source_id, rx_pps=None, tx_pps=None, rx_bps=None, tx_bps=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO traffic_data (source_id, timestamp, rx_pps, tx_pps, rx_bps, tx_bps)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (source_id, timestamp, rx_pps, tx_pps, rx_bps, tx_bps))
    conn.commit()
    conn.close()

# Data Retrieval
def get_environment_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM environment_data
    WHERE source_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def get_traffic_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM traffic_data
    WHERE source_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]
