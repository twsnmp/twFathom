import math

def calculate_anomaly(history, data_type, preprocess_type='residual', window_size=10, baseline_stats=None):
    """
    時系列データの異常度をホテリングのT^2法を用いて計算します。
    標準ライブラリのみで実装され、C拡張モジュール（NumPy/SciPyなど）は使用しません。

    引数:
        history (list): DBから取得した時系列データ（辞書のリスト）
        data_type (str): データ種別 ('environment', 'traffic', 'cpu_mem_disk', 'process_load', 'network_speed')
        preprocess_type (str): 前処理方法 ('raw', 'diff', 'residual')
            - 'raw': 生データ
            - 'diff': 1階差分
            - 'residual': 移動平均からの残差 (デフォルト)
        window_size (int): 移動平均の窓幅
        baseline_stats (dict): 事前計算された各カラムの平均と不偏分散の辞書 {col: (mean, variance)} (オプション)

    戻り値:
        dict: 異常検知結果（ステータス、メッセージ、過去の異常度リストなど）
    """
    columns_map = {
        'environment': ['temperature', 'humidity', 'soil_moisture', 'pressure', 'co2', 'illuminance'],
        'traffic': ['rx_pps', 'tx_pps', 'rx_bps', 'tx_bps'],
        'cpu_mem_disk': ['cpu', 'memory', 'disk'],
        'process_load': ['process', 'load'],
        'network_speed': ['tx_speed', 'rx_speed'],
        'occupancy': ['occupancy', 'illuminance', 'battery', 'linkquality', 'voltage', 'device_temperature', 'power_outage_count'],
        'contact': ['contact', 'battery', 'linkquality', 'voltage', 'device_temperature', 'power_outage_count', 'trigger_count']
    }
    
    cols = columns_map.get(data_type, [])
    if not cols or not history:
        return {
            "status": "nodata",
            "status_ja": "データなし",
            "message": "データがありません",
            "latest_score": 0.0,
            "latest_detail": {"score": 0.0, "max_col": None, "val": None},
            "scores": [],
            "timestamps": []
        }
        
    n = len(history)
    if n < 5:
        return {
            "status": "insufficient_data",
            "status_ja": "データ不足",
            "message": f"データ数が不足しています (現在: {n}件, 最低5件必要)",
            "latest_score": 0.0,
            "latest_detail": {"score": 0.0, "max_col": None, "val": None},
            "scores": [0.0] * n,
            "timestamps": [row.get('timestamp') for row in history]
        }
        
    # 各行の各カラムの異常度を格納するリスト
    anomaly_scores_by_row = [{} for _ in range(n)]
    raw_values_by_row = [{} for _ in range(n)]
    
    for col in cols:
        # 有効な値とその元のインデックスを抽出（NoneやNaNをスキップ）
        valid_points = []
        for i, row in enumerate(history):
            val = row.get(col)
            if val is not None and isinstance(val, (int, float)):
                valid_points.append((i, float(val)))
                raw_values_by_row[i][col] = float(val)
                
        if len(valid_points) < 5:
            continue  # 有効なデータ数が足りないカラムは無視
            
        # 前処理の適用
        preprocessed = []  # (original_row_index, preprocessed_value) のリスト
        
        if preprocess_type == 'diff':
            for idx in range(1, len(valid_points)):
                orig_idx = valid_points[idx][0]
                diff_val = valid_points[idx][1] - valid_points[idx-1][1]
                preprocessed.append((orig_idx, diff_val))
        elif preprocess_type == 'residual':
            running_sum = 0.0
            for idx in range(len(valid_points)):
                orig_idx = valid_points[idx][0]
                val = valid_points[idx][1]
                running_sum += val
                if idx >= window_size:
                    running_sum -= valid_points[idx - window_size][1]
                ma = running_sum / min(idx + 1, window_size)
                preprocessed.append((orig_idx, val - ma))
        else:  # 'raw'
            for idx in range(len(valid_points)):
                orig_idx = valid_points[idx][0]
                preprocessed.append((orig_idx, valid_points[idx][1]))
                
        # 前処理後の系列のデータ数チェック
        if len(preprocessed) < 5:
            continue
            
        # 平均と不偏分散を計算
        if baseline_stats and col in baseline_stats:
            mean, variance = baseline_stats[col]
        else:
            vals = [p[1] for p in preprocessed]
            mean = sum(vals) / len(vals)
            variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
        
        # ゼロ分散（値が全く変化しない）のエッジケースガード
        if variance < 1e-6:
            # 分散が極めて小さければ、このカラムの異常度は一律0とする（計算対象から除外）
            for orig_idx, _ in preprocessed:
                anomaly_scores_by_row[orig_idx][col] = 0.0
            continue
            
        # ホテリングのT^2値（異常度）を計算して格納
        for orig_idx, prep_val in preprocessed:
            score = ((prep_val - mean) ** 2) / variance
            anomaly_scores_by_row[orig_idx][col] = score
            
    # 総合異常度を算出
    scores = []
    timestamps = []
    details = []
    
    for i, row in enumerate(history):
        col_scores = anomaly_scores_by_row[i]
        max_col = None
        max_score = 0.0
        
        if col_scores:
            for col, score in col_scores.items():
                if score > max_score:
                    max_score = score
                    max_col = col
                    
        scores.append(max_score)
        timestamps.append(row.get('timestamp'))
        details.append({
            "score": max_score,
            "max_col": max_col,
            "val": raw_values_by_row[i].get(max_col) if max_col else None
        })
        
    latest_score = scores[-1] if scores else 0.0
    latest_detail = details[-1] if details else {"score": 0.0, "max_col": None, "val": None}
    
    # 閾値判定
    if latest_score > 6.63:
        status = "critical"
        status_ja = "異常"
    elif latest_score > 3.84:
        status = "warning"
        status_ja = "注意"
    else:
        status = "normal"
        status_ja = "正常"
        
    # 日本語の詳細メッセージ構築
    if status == "normal":
        message = f"状態: 正常 (異常度: {latest_score:.2f})"
    else:
        col_ja = latest_detail["max_col"]
        # 指標名の日本語マッピング
        col_names_ja = {
            'temperature': '温度', 'humidity': '湿度', 'soil_moisture': '土壌水分', 
            'pressure': '大気圧', 'co2': 'CO2 濃度', 'illuminance': '照度',
            'rx_pps': '受信パケット率', 'tx_pps': '送信パケット率', 
            'rx_bps': '受信速度', 'tx_bps': '送信速度',
            'cpu': 'CPU 使用率', 'memory': 'メモリ使用率', 'disk': 'ディスク使用率',
            'process': 'プロセス数', 'load': 'システム負荷',
            'tx_speed': '送信速度', 'rx_speed': '受信速度',
            'occupancy': '人感検知', 'battery': 'バッテリー残量', 'linkquality': 'リンク品質',
            'voltage': '電圧', 'device_temperature': 'デバイス温度', 'power_outage_count': '停電回数',
            'contact': '開閉状態', 'trigger_count': 'トリガー回数'
        }
        col_name = col_names_ja.get(col_ja, col_ja) if col_ja else "不明な指標"
        val_str = f"{latest_detail['val']:.2f}" if latest_detail['val'] is not None else "N/A"
        message = f"状態: {status_ja} (異常度: {latest_score:.2f} - 主因: {col_name} [{val_str}])"
        
    return {
        "status": status,
        "status_ja": status_ja,
        "message": message,
        "latest_score": latest_score,
        "latest_detail": latest_detail,
        "scores": scores,
        "timestamps": timestamps
    }
