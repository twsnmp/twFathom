import pytest
import sqlite3
from unittest.mock import patch
from datetime import datetime, timedelta
from twfathom.anomaly import calculate_anomaly

def make_dummy_history(values, key='cpu'):
    history = []
    base_time = datetime.now()
    for i, val in enumerate(values):
        ts = (base_time + timedelta(seconds=i*2)).isoformat()
        history.append({
            'timestamp': ts,
            key: val
        })
    return history

def test_normal_data():
    # ほぼ一定のデータ
    values = [10.0, 11.0, 10.0, 9.5, 10.0, 10.5, 10.0, 10.0, 9.5, 10.0, 10.0, 11.0, 10.0, 9.5, 10.0]
    history = make_dummy_history(values, 'cpu')
    result = calculate_anomaly(history, 'cpu_mem_disk')
    
    assert result['status'] == 'normal'
    assert result['latest_score'] <= 3.84
    assert len(result['scores']) == len(values)

def test_anomaly_spike():
    # 最後の値が急激に上昇（スパイク）
    values = [10.0, 11.0, 10.0, 9.5, 10.0, 10.5, 10.0, 10.0, 9.5, 10.0, 10.0, 11.0, 10.0, 9.5, 50.0]
    history = make_dummy_history(values, 'cpu')
    result = calculate_anomaly(history, 'cpu_mem_disk')
    
    assert result['status'] == 'critical'
    assert result['latest_score'] > 6.63
    assert result['latest_detail']['max_col'] == 'cpu'
    assert result['latest_detail']['val'] == 50.0

def test_zero_variance():
    # 全く変化しないデータ（分散が0になる）
    values = [100.0] * 15
    history = make_dummy_history(values, 'cpu')
    result = calculate_anomaly(history, 'cpu_mem_disk')
    
    # ガードロジックによりクラッシュせず、正常（異常度0）と判定されること
    assert result['status'] == 'normal'
    assert result['latest_score'] == 0.0
    assert all(s == 0.0 for s in result['scores'])

def test_missing_values():
    # 欠損値を含むデータ
    history = []
    base_time = datetime.now()
    values = [10.0, None, 11.0, 10.0, None, 9.5, 10.0, 10.5, 10.0, 10.0, None, 9.5, 10.0, 10.0, 50.0]
    for i, val in enumerate(values):
        ts = (base_time + timedelta(seconds=i*2)).isoformat()
        row = {'timestamp': ts}
        if val is not None:
            row['cpu'] = val
            row['memory'] = 20.0  # メモリは一定
        history.append(row)
        
    result = calculate_anomaly(history, 'cpu_mem_disk')
    
    assert result['status'] == 'critical'
    assert result['latest_score'] > 6.63
    assert result['latest_detail']['max_col'] == 'cpu'

def test_baseline_stats():
    # 正常なデータ
    values = [10.0, 11.0, 10.0, 9.5, 10.0, 10.5, 10.0, 10.0, 9.5, 10.0, 10.0, 11.0, 10.0, 9.5, 10.0]
    history = make_dummy_history(values, 'cpu')
    
    # 外部から与えた異常なベースライン (平均=100.0, 分散=1.0)
    # 実際の値(10.0前後)はベースライン(平均100.0)に対して大きな乖離があるため、異常判定されるはず
    baseline = {'cpu': (100.0, 1.0)}
    result = calculate_anomaly(history, 'cpu_mem_disk', baseline_stats=baseline)
    
    assert result['status'] == 'critical'
    assert result['latest_score'] > 6.63

def test_db_baseline_stats():
    from twfathom.db import get_baseline_stats
    
    # Set up in-memory sqlite3 database
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create environment_data table
    cursor.execute("""
    CREATE TABLE environment_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        temperature REAL,
        humidity REAL
    );
    """)
    
    # Insert 15 rows of dummy environment data
    # mean of temperature raw: 10.0
    base_time = datetime.now()
    for i in range(15):
        ts = (base_time + timedelta(seconds=i*2)).isoformat()
        temp = 10.0 + (1.0 if i % 2 == 0 else -1.0) # values: 11, 9, 11, 9...
        cursor.execute("""
        INSERT INTO environment_data (source_id, timestamp, temperature, humidity)
        VALUES (1, ?, ?, ?)
        """, (ts, temp, 50.0))
        
    conn.commit()
    
    # Mock db.get_db_connection to return this connection
    with patch('twfathom.db.get_db_connection', return_value=conn):
        stats = get_baseline_stats(1, 'environment', preprocess_type='residual', window_size=10)
        
    # Check stats calculated
    assert 'temperature' in stats
    mean, var = stats['temperature']
    
    # residual values should average around 0.0
    assert abs(mean) < 0.1
    # variance should be non-zero
    assert var > 0.1
    
    conn.close()


