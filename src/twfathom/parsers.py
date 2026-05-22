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
    Given a list of keys (headers), detect if it represents 'environment' or 'traffic' data.
    """
    env_matches = 0
    traffic_matches = 0
    
    for key in keys:
        key_lower = str(key).lower()
        if any(kw in key_lower for kw in ENV_KEYWORDS):
            env_matches += 1
        if any(kw in key_lower for kw in TRAFFIC_KEYWORDS):
            traffic_matches += 1
            
    if env_matches > traffic_matches:
        return 'environment'
    elif traffic_matches > env_matches:
        return 'traffic'
    return 'unknown'

def map_fields(data_dict, schema_type):
    """
    Maps a dictionary of arbitrary keys to the standard environment or traffic dictionary structure.
    """
    mapped = {}
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

def auto_parse_and_map(raw_content, filename=None):
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
