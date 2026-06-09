import csv
import json
import re

# Keyword sets for classification
ENV_KEYWORDS = {
    'temp', 'temperature', 'humidity', 'humid', 'pressure', 'co2', 'soil', 'moisture',
    'illu', 'illuminance', 'lux', 'light', '照度'
}

TRAFFIC_KEYWORDS = {
    'pps', 'bps', 'rx_pps', 'tx_pps', 'rx_bps', 'tx_bps', 'rx', 'tx', 'packets', 'bytes', 'traffic'
}

SYSTEM_RESOURCE_KEYWORDS = {
    'cpu', 'memory', 'mem', 'disk', 'storage', 'usage', '使用率'
}

SYSTEM_LOAD_KEYWORDS = {
    'load', 'process', 'proc', 'load_average', 'load_avg', 'プロセス', '負荷'
}

SYSTEM_SPEED_KEYWORDS = {
    'tx_speed', 'rx_speed', 'sent', 'recv', 'transmit_speed', 'receive_speed', 'speed', '通信', '送信', '受信'
}

# Mapping patterns using regular expressions for flexible naming
ENV_MAPS = {
    'temperature': [re.compile(r'temp(erature)?$', re.I), re.compile(r'^t$', re.I)],
    'humidity': [re.compile(r'humid(ity)?$', re.I), re.compile(r'^h$', re.I)],
    'pressure': [re.compile(r'press(ure)?$', re.I), re.compile(r'^p$', re.I)],
    'co2': [re.compile(r'co2$', re.I), re.compile(r'carbon$', re.I)],
    'soil_moisture': [re.compile(r'soil(_moisture)?$', re.I), re.compile(r'moisture$', re.I), re.compile(r'^sm$', re.I)],
    'illuminance': [re.compile(r'illu(minance)?$', re.I), re.compile(r'lux$', re.I), re.compile(r'light$', re.I), re.compile(r'^l$', re.I), re.compile(r'照度$', re.I)]
}

TRAFFIC_MAPS = {
    'rx_pps': [re.compile(r'rx_?pps$', re.I), re.compile(r'rx_?packets?$', re.I), re.compile(r'r_?pps$', re.I)],
    'tx_pps': [re.compile(r'tx_?pps$', re.I), re.compile(r'tx_?packets?$', re.I), re.compile(r't_?pps$', re.I)],
    'rx_bps': [re.compile(r'rx_?bps$', re.I), re.compile(r'rx_?bytes?$', re.I), re.compile(r'r_?bps$', re.I)],
    'tx_bps': [re.compile(r'tx_?bps$', re.I), re.compile(r'tx_?bytes?$', re.I), re.compile(r't_?bps$', re.I)]
}

SYSTEM_RESOURCE_MAPS = {
    'cpu': [re.compile(r'cpu(_usage|_utilization)?$', re.I), re.compile(r'^cpu$', re.I)],
    'memory': [re.compile(r'mem(ory)?(_usage|_utilization)?$', re.I), re.compile(r'^memory$', re.I), re.compile(r'^mem$', re.I)],
    'disk': [re.compile(r'disk(_usage|_utilization)?$', re.I), re.compile(r'^disk$', re.I), re.compile(r'storage$', re.I)]
}

SYSTEM_LOAD_MAPS = {
    'process': [re.compile(r'process(es|_count)?$', re.I), re.compile(r'^proc(s)?$', re.I), re.compile(r'^process$', re.I), re.compile(r'プロセス数?$', re.I)],
    'load': [re.compile(r'load(_average|_avg)?$', re.I), re.compile(r'^load$', re.I), re.compile(r'負荷$', re.I)]
}

SYSTEM_SPEED_MAPS = {
    'sent': [re.compile(r'sent$', re.I), re.compile(r'tx_?bytes$', re.I), re.compile(r'送信バイト?$', re.I)],
    'recv': [re.compile(r'recv$', re.I), re.compile(r'rx_?bytes$', re.I), re.compile(r'受信バイト?$', re.I)],
    'tx_speed': [re.compile(r'tx_?speed$', re.I), re.compile(r'transmit_?speed$', re.I), re.compile(r'送信速度$', re.I)],
    'rx_speed': [re.compile(r'rx_?speed$', re.I), re.compile(r'receive_?speed$', re.I), re.compile(r'受信速度$', re.I)]
}

TIMESTAMP_MAPS = [
    re.compile(r'time(stamp)?$', re.I),
    re.compile(r'date(time)?$', re.I),
    re.compile(r'^dt$', re.I),
    re.compile(r'時刻$', re.I),
    re.compile(r'日付$', re.I),
    re.compile(r'日時$', re.I)
]

def match_key(key, patterns):
    """
    Checks if a key (or its nested parts) matches any of the given patterns.
    E.g., "main_temp" should match a pattern for "temp" or "temperature".
    """
    key_str = str(key).strip()
    # 1. Exact match / full match on the whole key
    if any(pat.match(key_str) for pat in patterns):
        return True
        
    # 2. Match sub-parts joined by underscore from right to left
    # e.g. "device_rx_pps" -> check "rx_pps", then "pps"
    parts = key_str.split('_')
    if len(parts) > 1:
        for i in range(1, len(parts)):
            sub_key = '_'.join(parts[i:])
            if any(pat.match(sub_key) for pat in patterns):
                return True
                
    return False

def detect_data_type(keys):
    """
    Given a list of keys (headers), detect if it represents 'environment', 'traffic',
    'cpu_mem_disk', 'process_load', or 'network_speed' data.
    """
    env_matches = 0
    traffic_matches = 0
    cpu_mem_disk_matches = 0
    process_load_matches = 0
    network_speed_matches = 0
    
    for key in keys:
        key_lower = str(key).lower()
        if any(kw in key_lower for kw in ENV_KEYWORDS):
            env_matches += 1
        if any(kw in key_lower for kw in TRAFFIC_KEYWORDS):
            traffic_matches += 1
        if any(kw in key_lower for kw in SYSTEM_RESOURCE_KEYWORDS):
            cpu_mem_disk_matches += 1
        if any(kw in key_lower for kw in SYSTEM_LOAD_KEYWORDS):
            process_load_matches += 1
        if any(kw in key_lower for kw in SYSTEM_SPEED_KEYWORDS):
            network_speed_matches += 1
            
    matches = {
        'environment': env_matches,
        'traffic': traffic_matches,
        'cpu_mem_disk': cpu_mem_disk_matches,
        'process_load': process_load_matches,
        'network_speed': network_speed_matches
    }
    
    best_type = 'unknown'
    max_match = 0
    for t, m in matches.items():
        if m > max_match:
            max_match = m
            best_type = t
            
    return best_type

def map_fields(data_dict, schema_type):
    """
    Maps a dictionary of arbitrary keys to the standard environment, traffic,
    cpu_mem_disk, process_load, or network_speed dictionary structure.
    Includes mapping for an optional timestamp field.
    """
    mapped = {}
    
    # 1. Map optional timestamp field if present
    mapped['timestamp'] = None
    for key, val in data_dict.items():
        if match_key(key, TIMESTAMP_MAPS):
            try:
                # Handle numeric UNIX timestamps (e.g. 1779476805)
                val_float = float(val)
                if val_float > 1000000000:
                    from datetime import datetime
                    mapped['timestamp'] = datetime.fromtimestamp(val_float).isoformat()
                else:
                    mapped['timestamp'] = str(val).strip()
            except (ValueError, TypeError):
                mapped['timestamp'] = str(val).strip()
            break
            
    # 2. Map schema-specific fields
    if schema_type == 'environment':
        for target, patterns in ENV_MAPS.items():
            mapped[target] = None
            for key, val in data_dict.items():
                if match_key(key, patterns):
                    try:
                        mapped[target] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass
    elif schema_type == 'traffic':
        for target, patterns in TRAFFIC_MAPS.items():
            mapped[target] = None
            for key, val in data_dict.items():
                if match_key(key, patterns):
                    try:
                        mapped[target] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass
    elif schema_type == 'cpu_mem_disk':
        for target, patterns in SYSTEM_RESOURCE_MAPS.items():
            mapped[target] = None
            for key, val in data_dict.items():
                if match_key(key, patterns):
                    try:
                        mapped[target] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass
    elif schema_type == 'process_load':
        for target, patterns in SYSTEM_LOAD_MAPS.items():
            mapped[target] = None
            for key, val in data_dict.items():
                if match_key(key, patterns):
                    try:
                        if target == 'process':
                            mapped[target] = int(float(val))
                        else:
                            mapped[target] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass
    elif schema_type == 'network_speed':
        for target, patterns in SYSTEM_SPEED_MAPS.items():
            mapped[target] = None
            for key, val in data_dict.items():
                if match_key(key, patterns):
                    try:
                        mapped[target] = float(val)
                        break
                    except (ValueError, TypeError):
                        pass
    return mapped

def flatten_dict(d, parent_key='', sep='_'):
    """
    Recursively flattens a nested dictionary.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def parse_json(json_str):
    """
    Parses a JSON string into a list of flat dictionaries.
    Supports a list of objects or a single object.
    """
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return [flatten_dict(item) for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            return [flatten_dict(data)]
    except Exception:
        pass
    return []

def parse_csv(csv_str):
    """
    Parses a CSV string into a list of dictionaries.
    """
    try:
        reader = csv.DictReader(csv_str.splitlines())
        return [dict(row) for row in reader]
    except Exception:
        return []

def auto_parse_and_map(raw_content, expected_type=None):
    """
    Automatically parses the raw text based on whether it is CSV, JSON,
    and returns a tuple (data_type, mapped_list).
    """
    raw_content = raw_content.strip()
    
    # 1. Parse into a list of flat dictionaries
    parsed_rows = []
    if raw_content.startswith('{') or raw_content.startswith('['):
        parsed_rows = parse_json(raw_content)
    else:
        # Default to CSV if it looks like columns
        parsed_rows = parse_csv(raw_content)
        
    if not parsed_rows:
        return 'unknown', []
        
    # 2. Get keys/headers from the first row to detect data type
    sample_keys = parsed_rows[0].keys()
    
    if expected_type and expected_type != 'unknown':
        detected_type = expected_type
    else:
        detected_type = detect_data_type(sample_keys)
    
    if detected_type == 'unknown':
        return 'unknown', []
        
    # 3. Map all rows into the detected schema type
    mapped_rows = []
    for row in parsed_rows:
        mapped_row = map_fields(row, detected_type)
        # Ensure we have at least some mapped fields with actual data
        if any(v is not None for v in mapped_row.values()):
            mapped_rows.append(mapped_row)
            
    return detected_type, mapped_rows
