import threading
import time
import os
import httpx
import paho.mqtt.client as mqtt
from .db import (
    insert_environment_data, 
    insert_traffic_data, 
    get_source, 
    update_source,
    get_sources
)
from .parsers import auto_parse_and_map

# Active background collector threads and events
RUNNING_COLLECTORS = {}

def https_poll_loop(source_id, config, interval, stop_event):
    url = config.get("url")
    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})
    params = config.get("params", {})
    
    print(f"\n[HTTPS Collector {source_id}] Starting poller for {url} (interval: {interval}s)...")
    
    while not stop_event.is_set():
        try:
            print(f"[HTTPS Collector {source_id}] Polling {method} {url}...")
            with httpx.Client(timeout=10.0) as client:
                if method == "POST":
                    resp = client.post(url, headers=headers, json=params)
                else:
                    resp = client.get(url, headers=headers)
                
                print(f"[HTTPS Collector {source_id}] Response received (status code: {resp.status_code})")
                if resp.status_code == 200:
                    raw_data = resp.text
                    source = get_source(source_id)
                    if source:
                        data_type, mapped_rows = auto_parse_and_map(raw_data)
                        print(f"[HTTPS Collector {source_id}] Parsed type: {data_type}, rows found: {len(mapped_rows) if mapped_rows else 0}")
                        if data_type != 'unknown' and mapped_rows:
                            if source['data_type'] == 'unknown':
                                print(f"[HTTPS Collector {source_id}] Auto-detected source data_type: {data_type}. Updating DB...")
                                update_source(
                                    source_id, source['name'], source['type'],
                                    source['config'], source['interval'], data_type, source['active']
                                )
                            
                            for row in mapped_rows:
                                if data_type == 'environment':
                                    insert_environment_data(
                                        source_id, 
                                        temperature=row.get('temperature'),
                                        humidity=row.get('humidity'),
                                        pressure=row.get('pressure'),
                                        co2=row.get('co2'),
                                        soil_moisture=row.get('soil_moisture'),
                                        illuminance=row.get('illuminance'),
                                        timestamp=row.get('timestamp')
                                    )
                                    print(f"  Inserted Environment: Temp={row.get('temperature')}, Humid={row.get('humidity')}, Lux={row.get('illuminance')}")
                                elif data_type == 'traffic':
                                    insert_traffic_data(
                                        source_id,
                                        rx_pps=row.get('rx_pps'),
                                        tx_pps=row.get('tx_pps'),
                                        rx_bps=row.get('rx_bps'),
                                        tx_bps=row.get('tx_bps'),
                                        timestamp=row.get('timestamp')
                                    )
                                    print(f"  Inserted Traffic: RxBps={row.get('rx_bps')}, TxBps={row.get('tx_bps')}")
        except Exception as e:
            print(f"[HTTPS Collector {source_id}] Error polling source: {e}")
            
        # Sleep in tiny increments so we can exit quickly when stop_event is set
        for _ in range(max(1, int(interval))):
            if stop_event.is_set():
                break
            time.sleep(1)

def file_poll_loop(source_id, config, interval, stop_event):
    filepath = config.get("filepath")
    last_mtime = 0
    
    print(f"\n[File Collector {source_id}] Starting watch on {filepath} (interval: {interval}s)...")
    
    while not stop_event.is_set():
        try:
            if filepath and os.path.exists(filepath):
                mtime = os.path.getmtime(filepath)
                if mtime > last_mtime:
                    print(f"[File Collector {source_id}] File updated (mtime: {mtime}). Reading...")
                    last_mtime = mtime
                    with open(filepath, 'r', encoding='utf-8') as f:
                        raw_data = f.read()
                    
                    source = get_source(source_id)
                    if source:
                        data_type, mapped_rows = auto_parse_and_map(raw_data)
                        print(f"[File Collector {source_id}] Parsed type: {data_type}, rows found: {len(mapped_rows) if mapped_rows else 0}")
                        if data_type != 'unknown' and mapped_rows:
                            if source['data_type'] == 'unknown':
                                print(f"[File Collector {source_id}] Auto-detected source data_type: {data_type}. Updating DB...")
                                update_source(
                                    source_id, source['name'], source['type'],
                                    source['config'], source['interval'], data_type, source['active']
                                )
                            
                            for row in mapped_rows:
                                if data_type == 'environment':
                                    insert_environment_data(
                                        source_id, 
                                        temperature=row.get('temperature'),
                                        humidity=row.get('humidity'),
                                        pressure=row.get('pressure'),
                                        co2=row.get('co2'),
                                        soil_moisture=row.get('soil_moisture'),
                                        illuminance=row.get('illuminance'),
                                        timestamp=row.get('timestamp')
                                    )
                                    print(f"  Inserted Environment: Temp={row.get('temperature')}, Humid={row.get('humidity')}, Lux={row.get('illuminance')}")
                                elif data_type == 'traffic':
                                    insert_traffic_data(
                                        source_id,
                                        rx_pps=row.get('rx_pps'),
                                        tx_pps=row.get('tx_pps'),
                                        rx_bps=row.get('rx_bps'),
                                        tx_bps=row.get('tx_bps'),
                                        timestamp=row.get('timestamp')
                                    )
                                    print(f"  Inserted Traffic: RxBps={row.get('rx_bps')}, TxBps={row.get('tx_bps')}")
            elif filepath and not os.path.exists(filepath):
                print(f"[File Collector {source_id}] File does not exist: {filepath}")
        except Exception as e:
            print(f"[File Collector {source_id}] Error polling File: {e}")
            
        for _ in range(max(1, int(interval))):
            if stop_event.is_set():
                break
            time.sleep(1)

def mqtt_listener(source_id, config, stop_event):
    broker = config.get("broker")
    port = int(config.get("port", 1883))
    username = config.get("username")
    password = config.get("password")
    topic = config.get("topic", "#")
    
    print(f"\n[MQTT Collector {source_id}] Initializing MQTT listener for broker {broker}:{port}...")
    
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    if username:
        print(f"[MQTT Collector {source_id}] Setting credentials for user '{username}'")
        client.username_pw_set(username, password)
    else:
        print(f"[MQTT Collector {source_id}] No username provided, connecting anonymously")
        
    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"[MQTT Collector {source_id}] SUCCESS: Connected to MQTT broker {broker}:{port}")
            print(f"[MQTT Collector {source_id}] Subscribing to topic: {topic}")
            client.subscribe(topic)
        else:
            print(f"[MQTT Collector {source_id}] FAILURE: Failed to connect to broker, reason code: {reason_code}")
            
    def on_subscribe(client, userdata, mid, reason_codes, properties=None):
        print(f"[MQTT Collector {source_id}] SUCCESS: Subscribed to topic mid {mid}")

    def on_message(client_inst, userdata, msg):
        try:
            raw_payload = msg.payload.decode('utf-8', errors='ignore')
            print(f"\n[MQTT Collector {source_id}] Message received on topic '{msg.topic}':")
            print(f"  Payload: {raw_payload}")
            
            source = get_source(source_id)
            if source:
                data_type, mapped_rows = auto_parse_and_map(raw_payload)
                print(f"  Auto-parse result -> type: {data_type}, rows found: {len(mapped_rows) if mapped_rows else 0}")
                if data_type != 'unknown' and mapped_rows:
                    if source['data_type'] == 'unknown':
                        print(f"  First data received! Updating source data_type to: {data_type}")
                        update_source(
                            source_id, source['name'], source['type'],
                            source['config'], source['interval'], data_type, source['active']
                        )
                    
                    for row in mapped_rows:
                        if data_type == 'environment':
                            insert_environment_data(
                                source_id, 
                                temperature=row.get('temperature'),
                                humidity=row.get('humidity'),
                                pressure=row.get('pressure'),
                                co2=row.get('co2'),
                                soil_moisture=row.get('soil_moisture'),
                                illuminance=row.get('illuminance'),
                                timestamp=row.get('timestamp')
                            )
                            print(f"  Inserted Environment: Temp={row.get('temperature')}, Humid={row.get('humidity')}, Lux={row.get('illuminance')}")
                        elif data_type == 'traffic':
                            insert_traffic_data(
                                source_id,
                                rx_pps=row.get('rx_pps'),
                                tx_pps=row.get('tx_pps'),
                                rx_bps=row.get('rx_bps'),
                                tx_bps=row.get('tx_bps'),
                                timestamp=row.get('timestamp')
                            )
                            print(f"  Inserted Traffic: RxBps={row.get('rx_bps')}, TxBps={row.get('tx_bps')}")
                else:
                    print("  Warning: Message payload was not mapped to any known data schema (environment or traffic).")
        except Exception as e:
            print(f"[MQTT Collector {source_id}] Error in MQTT message callback: {e}")
            
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    
    try:
        client.connect(broker, port, 60)
        client.loop_start()
        
        while not stop_event.is_set():
            time.sleep(1)
            
        client.loop_stop()
        client.disconnect()
        print(f"[MQTT Collector {source_id}] Gracefully disconnected from broker.")
    except Exception as e:
        print(f"[MQTT Collector {source_id}] MQTT client error: {e}")

def start_collector(source_id):
    """
    Spawns the background collector thread for a specific source if it is active.
    """
    if source_id in RUNNING_COLLECTORS:
        # Already running, stop first
        stop_collector(source_id)
        
    source = get_source(source_id)
    if not source or not source.get("active"):
        return
        
    stop_event = threading.Event()
    source_type = source["type"]
    config = source["config"]
    interval = source["interval"]
    
    if source_type == "https":
        t = threading.Thread(target=https_poll_loop, args=(source_id, config, interval, stop_event), daemon=True)
    elif source_type == "file":
        t = threading.Thread(target=file_poll_loop, args=(source_id, config, interval, stop_event), daemon=True)
    elif source_type == "mqtt":
        t = threading.Thread(target=mqtt_listener, args=(source_id, config, stop_event), daemon=True)
    else:
        return
        
    RUNNING_COLLECTORS[source_id] = (t, stop_event)
    t.start()

def stop_collector(source_id):
    """
    Stops a running collector thread.
    """
    if source_id in RUNNING_COLLECTORS:
        t, stop_event = RUNNING_COLLECTORS.pop(source_id)
        stop_event.set()
        t.join(timeout=2.0)

def start_all_collectors():
    """
    Spawns background collectors for all active sources in the database.
    """
    sources = get_sources()
    for s in sources:
        if s.get("active"):
            start_collector(s["id"])

def stop_all_collectors():
    """
    Stops all background collectors.
    """
    active_ids = list(RUNNING_COLLECTORS.keys())
    for s_id in active_ids:
        stop_collector(s_id)
