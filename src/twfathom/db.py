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
        illuminance REAL,
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
    
    # 4. cpu_mem_disk_data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpu_mem_disk_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        cpu REAL,
        memory REAL,
        disk REAL,
        FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
    );
    """)

    # 5. process_load_data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS process_load_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        process INTEGER,
        load REAL,
        FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
    );
    """)

    # 6. network_speed_data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_speed_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        sent REAL,
        recv REAL,
        tx_speed REAL,
        rx_speed REAL,
        FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
    );
    """)
    
    # Create indexes for time series queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_env_source_time ON environment_data (source_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_source_time ON traffic_data (source_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpu_mem_disk_source_time ON cpu_mem_disk_data (source_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_process_load_source_time ON process_load_data (source_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_network_speed_source_time ON network_speed_data (source_id, timestamp);")
    
    # Check for legacy databases and migrate schema
    cursor.execute("PRAGMA table_info(sources);")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'data_type' not in columns:
        cursor.execute("ALTER TABLE sources ADD COLUMN data_type TEXT NOT NULL DEFAULT 'unknown';")
    if 'active' not in columns:
        cursor.execute("ALTER TABLE sources ADD COLUMN active INTEGER DEFAULT 1;")
        
    cursor.execute("PRAGMA table_info(environment_data);")
    env_columns = [row['name'] for row in cursor.fetchall()]
    if 'illuminance' not in env_columns:
        cursor.execute("ALTER TABLE environment_data ADD COLUMN illuminance REAL;")
        
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
def insert_environment_data(source_id, temperature=None, humidity=None, pressure=None, co2=None, soil_moisture=None, illuminance=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO environment_data (source_id, timestamp, temperature, humidity, pressure, co2, soil_moisture, illuminance)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (source_id, timestamp, temperature, humidity, pressure, co2, soil_moisture, illuminance))
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

def insert_cpu_mem_disk_data(source_id, cpu=None, memory=None, disk=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO cpu_mem_disk_data (source_id, timestamp, cpu, memory, disk)
    VALUES (?, ?, ?, ?, ?)
    """, (source_id, timestamp, cpu, memory, disk))
    conn.commit()
    conn.close()

def insert_process_load_data(source_id, process=None, load=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO process_load_data (source_id, timestamp, process, load)
    VALUES (?, ?, ?, ?)
    """, (source_id, timestamp, process, load))
    conn.commit()
    conn.close()

def insert_network_speed_data(source_id, sent=None, recv=None, tx_speed=None, rx_speed=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO network_speed_data (source_id, timestamp, sent, recv, tx_speed, rx_speed)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (source_id, timestamp, sent, recv, tx_speed, rx_speed))
    conn.commit()
    conn.close()

# Data Retrieval
def get_environment_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    if limit is None or limit <= 0:
        cursor.execute("""
        SELECT * FROM environment_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        """, (source_id,))
    else:
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
    if limit is None or limit <= 0:
        cursor.execute("""
        SELECT * FROM traffic_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        """, (source_id,))
    else:
        cursor.execute("""
        SELECT * FROM traffic_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def get_cpu_mem_disk_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    if limit is None or limit <= 0:
        cursor.execute("""
        SELECT * FROM cpu_mem_disk_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        """, (source_id,))
    else:
        cursor.execute("""
        SELECT * FROM cpu_mem_disk_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def get_process_load_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    if limit is None or limit <= 0:
        cursor.execute("""
        SELECT * FROM process_load_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        """, (source_id,))
    else:
        cursor.execute("""
        SELECT * FROM process_load_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def get_network_speed_history(source_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    if limit is None or limit <= 0:
        cursor.execute("""
        SELECT * FROM network_speed_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        """, (source_id,))
    else:
        cursor.execute("""
        SELECT * FROM network_speed_data
        WHERE source_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (source_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def clear_source_data(source_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM environment_data WHERE source_id = ?", (source_id,))
    cursor.execute("DELETE FROM traffic_data WHERE source_id = ?", (source_id,))
    cursor.execute("DELETE FROM cpu_mem_disk_data WHERE source_id = ?", (source_id,))
    cursor.execute("DELETE FROM process_load_data WHERE source_id = ?", (source_id,))
    cursor.execute("DELETE FROM network_speed_data WHERE source_id = ?", (source_id,))
    conn.commit()
    conn.close()
