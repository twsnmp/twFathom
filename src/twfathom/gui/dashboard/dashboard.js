let sourceId = null;
let chart = null;
let dataType = 'unknown';
let lastDataSignature = '';

// Parse query params to get source ID
const urlParams = new URLSearchParams(window.location.search);
sourceId = parseInt(urlParams.get('id'), 10);

function formatBytes(bytes) {
    if (bytes === null || bytes === undefined || isNaN(bytes)) return { value: '0', unit: 'bps' };
    if (bytes < 1000) return { value: bytes.toFixed(1), unit: 'bps' };
    if (bytes < 1000000) return { value: (bytes / 1000).toFixed(1), unit: 'Kbps' };
    if (bytes < 1000000000) return { value: (bytes / 1000000).toFixed(1), unit: 'Mbps' };
    return { value: (bytes / 1000000000).toFixed(1), unit: 'Gbps' };
}

function formatNumber(num, decimals = 1) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return num.toFixed(decimals);
}

// Initialise ECharts with premium dark theme configuration
function initChart(type, data) {
    const chartDom = document.getElementById('main-chart');
    if (!chartDom) return;
    
    if (!chart) {
        chart = echarts.init(chartDom);
        // Make responsive
        window.addEventListener('resize', () => {
            if (chart) chart.resize();
        });
    }
    
    let option = {};
    const timestamps = data.map(d => {
        // Parse ISO timestamp to readable time
        try {
            const dt = new Date(d.timestamp);
            return dt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch(e) {
            return d.timestamp;
        }
    });
    
    const baseGrid = {
        left: '4%',
        right: '4%',
        bottom: '60px',
        top: '45px',
        containLabel: true
    };
    
    const baseTooltip = {
        trigger: 'axis',
        backgroundColor: 'rgba(23, 25, 35, 0.9)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        textStyle: { color: '#f3f4f6' },
        axisPointer: { type: 'cross' }
    };
    
    // Dynamically focus on the latest 30 points if the history becomes long,
    // while still letting the user zoom out/pan backwards.
    let startZoom = 0;
    if (data.length > 30) {
        startZoom = Math.round((1 - 30 / data.length) * 100);
    }
    
    const baseDataZoom = [
        {
            type: 'slider',
            show: true,
            xAxisIndex: [0],
            start: startZoom,
            end: 100,
            height: 16,
            bottom: 12,
            borderColor: 'rgba(255, 255, 255, 0.08)',
            backgroundColor: 'rgba(255, 255, 255, 0.01)',
            fillerColor: 'rgba(0, 210, 255, 0.08)',
            handleIcon: 'path://M-1.5,0.5c0-0.2,0.1-0.4,0.3-0.5c0.2-0.1,0.4-0.1,0.6,0c0.2,0.1,0.3,0.3,0.3,0.5v15c0,0.2-0.1,0.4-0.3,0.5c-0.2,0.1-0.4,0.1-0.6,0c-0.2-0.1-0.3-0.3-0.3-0.5V0.5z',
            handleSize: '120%',
            handleStyle: {
                color: '#00d2ff',
                borderColor: 'rgba(0, 210, 255, 0.4)',
                shadowBlur: 3,
                shadowColor: 'rgba(0, 210, 255, 0.2)'
            },
            moveHandleStyle: {
                color: 'rgba(0, 210, 255, 0.2)'
            },
            textStyle: {
                color: '#9ca3af',
                fontFamily: 'Inter',
                fontSize: 9
            },
            brushSelect: false
        },
        {
            type: 'inside',
            xAxisIndex: [0],
            start: startZoom,
            end: 100,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true
        }
    ];
    
    if (type === 'environment') {
        const ENV_FIELDS = {
            temperature: {
                name: '温度 (°C)',
                color: '#ef4444',
                areaColor: 'rgba(239, 68, 68, 0.2)'
            },
            humidity: {
                name: '湿度 (%)',
                color: '#00d2ff',
                areaColor: 'rgba(0, 210, 255, 0.2)'
            },
            soil_moisture: {
                name: '土壌水分 (%)',
                color: '#00f5d4',
                areaColor: 'rgba(0, 245, 212, 0.2)'
            },
            pressure: {
                name: '気圧 (hPa)',
                color: '#10b981',
                areaColor: 'rgba(16, 185, 129, 0.2)'
            },
            co2: {
                name: 'CO2 (ppm)',
                color: '#f59e0b',
                areaColor: 'rgba(245, 158, 11, 0.2)'
            },
            illuminance: {
                name: '照度 (lx)',
                color: '#bd00ff',
                areaColor: 'rgba(189, 0, 255, 0.2)'
            }
        };

        const hasData = (key) => data.some(d => d[key] !== null && d[key] !== undefined);
        const otherKeys = ['soil_moisture', 'pressure', 'co2', 'illuminance'];
        const activeOtherKey = otherKeys.find(hasData);

        let legendData = [];
        let yAxisConfig = [];
        let seriesConfig = [];

        if (!activeOtherKey) {
            // Case 1: Only Temperature and Humidity (or fewer/no others)
            legendData = [ENV_FIELDS.temperature.name, ENV_FIELDS.humidity.name];
            
            yAxisConfig = [
                {
                    type: 'value',
                    name: '温度',
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: '湿度',
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ];

            seriesConfig = [
                {
                    name: ENV_FIELDS.temperature.name,
                    type: 'line',
                    smooth: true,
                    data: data.map(d => d.temperature),
                    itemStyle: { color: ENV_FIELDS.temperature.color },
                    lineStyle: { width: 3 },
                    yAxisIndex: 0,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: ENV_FIELDS.temperature.areaColor },
                            { offset: 1, color: 'rgba(239, 68, 68, 0)' }
                        ])
                    }
                },
                {
                    name: ENV_FIELDS.humidity.name,
                    type: 'line',
                    smooth: true,
                    data: data.map(d => d.humidity),
                    itemStyle: { color: ENV_FIELDS.humidity.color },
                    lineStyle: { width: 3 },
                    yAxisIndex: 1,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: ENV_FIELDS.humidity.areaColor },
                            { offset: 1, color: 'rgba(0, 210, 255, 0)' }
                        ])
                    }
                }
            ];
        } else {
            // Case 2: Other data types exist (Soil Moisture, Atmospheric Pressure, CO2, or Illuminance)
            legendData = [ENV_FIELDS.temperature.name, ENV_FIELDS.humidity.name, ENV_FIELDS[activeOtherKey].name];

            yAxisConfig = [
                {
                    type: 'value',
                    name: '温湿度',
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: ENV_FIELDS[activeOtherKey].name.split(' ')[0], // Name without unit for the axis title
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ];

            seriesConfig = [
                {
                    name: ENV_FIELDS.temperature.name,
                    type: 'line',
                    smooth: true,
                    data: data.map(d => d.temperature),
                    itemStyle: { color: ENV_FIELDS.temperature.color },
                    lineStyle: { width: 3 },
                    yAxisIndex: 0,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: ENV_FIELDS.temperature.areaColor },
                            { offset: 1, color: 'rgba(239, 68, 68, 0)' }
                        ])
                    }
                },
                {
                    name: ENV_FIELDS.humidity.name,
                    type: 'line',
                    smooth: true,
                    data: data.map(d => d.humidity),
                    itemStyle: { color: ENV_FIELDS.humidity.color },
                    lineStyle: { width: 3 },
                    yAxisIndex: 0,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: ENV_FIELDS.humidity.areaColor },
                            { offset: 1, color: 'rgba(0, 210, 255, 0)' }
                        ])
                    }
                },
                {
                    name: ENV_FIELDS[activeOtherKey].name,
                    type: 'line',
                    smooth: true,
                    data: data.map(d => d[activeOtherKey]),
                    itemStyle: { color: ENV_FIELDS[activeOtherKey].color },
                    lineStyle: { width: 3 },
                    yAxisIndex: 1,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: ENV_FIELDS[activeOtherKey].areaColor },
                            { offset: 1, color: 'rgba(0, 0, 0, 0)' }
                        ])
                    }
                }
            ];
        }

        option = {
            backgroundColor: 'transparent',
            tooltip: baseTooltip,
            legend: {
                data: legendData,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: timestamps,
                axisLabel: { color: '#9ca3af' },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: yAxisConfig,
            series: seriesConfig
        };
    } else if (type === 'traffic') {
        const rxPPS = data.map(d => d.rx_pps);
        const txPPS = data.map(d => d.tx_pps);
        const rxBPS = data.map(d => d.rx_bps);
        const txBPS = data.map(d => d.tx_bps);
        
        option = {
            backgroundColor: 'transparent',
            tooltip: baseTooltip,
            legend: {
                data: ['受信 (pps)', '送信 (pps)', '受信速度 (bps)', '送信速度 (bps)'],
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: timestamps,
                axisLabel: { color: '#9ca3af' },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: [
                {
                    type: 'value',
                    name: 'パケットレート (pps)',
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: 'ビットレート (bps)',
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ],
            series: [
                {
                    name: '受信 (pps)',
                    type: 'line',
                    smooth: true,
                    data: rxPPS,
                    itemStyle: { color: '#00d2ff' },
                    lineStyle: { width: 3 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 210, 255, 0.2)' },
                            { offset: 1, color: 'rgba(0, 210, 255, 0)' }
                        ])
                    }
                },
                {
                    name: '送信 (pps)',
                    type: 'line',
                    smooth: true,
                    data: txPPS,
                    itemStyle: { color: '#bd00ff' },
                    lineStyle: { width: 3 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(189, 0, 255, 0.2)' },
                            { offset: 1, color: 'rgba(189, 0, 255, 0)' }
                        ])
                    }
                },
                {
                    name: '受信速度 (bps)',
                    type: 'line',
                    smooth: true,
                    yAxisIndex: 1,
                    data: rxBPS,
                    itemStyle: { color: '#00f5d4' },
                    lineStyle: { width: 2, type: 'dashed' }
                },
                {
                    name: '送信速度 (bps)',
                    type: 'line',
                    smooth: true,
                    yAxisIndex: 1,
                    data: txBPS,
                    itemStyle: { color: '#f59e0b' },
                    lineStyle: { width: 2, type: 'dashed' }
                }
            ]
        };
    }
    
    chart.setOption(option, true);
}

// Refresh KPI Cards
function updateKpiCards(type, latestData) {
    const list = document.getElementById('kpi-list');
    if (!list) return;
    
    list.innerHTML = '';
    
    if (!latestData) {
        list.innerHTML = `<div class="glass-card" style="width: 100%; text-align: center; color: var(--text-muted);">まだデータが受信されていません。データソースを監視しています...</div>`;
        return;
    }
    
    if (type === 'environment') {
        const fields = [
            { label: '温度', val: latestData.temperature, unit: '°C', color: 'var(--color-danger)' },
            { label: '湿度', val: latestData.humidity, unit: '%', color: 'var(--color-primary)' },
            { label: '土壌水分', val: latestData.soil_moisture, unit: '%', color: '#00f5d4' },
            { label: '大気圧', val: latestData.pressure, unit: 'hPa', color: 'var(--color-success)' },
            { label: 'CO2 濃度', val: latestData.co2, unit: 'ppm', color: 'var(--color-warning)' },
            { label: '照度', val: latestData.illuminance, unit: 'lx', color: '#bd00ff' }
        ];
        
        fields.forEach(f => {
            if (f.val === null || f.val === undefined) return;
            
            const card = document.createElement('div');
            card.className = 'glass-card kpi-card';
            card.style.setProperty('--card-accent', f.color);
            
            card.innerHTML = `
                <span class="kpi-title">${f.label}</span>
                <div class="kpi-value">${formatNumber(f.val)}<span class="kpi-unit">${f.unit}</span></div>
            `;
            list.appendChild(card);
        });
    } else if (type === 'traffic') {
        const rxB = formatBytes(latestData.rx_bps);
        const txB = formatBytes(latestData.tx_bps);
        
        const fields = [
            { label: '受信パケット率 (Rx)', val: latestData.rx_pps, unit: 'pps', color: 'var(--color-primary)' },
            { label: '送信パケット率 (Tx)', val: latestData.tx_pps, unit: 'pps', color: 'var(--color-secondary)' },
            { label: '受信スループット', val: parseFloat(rxB.value), unit: rxB.unit, color: '#00f5d4' },
            { label: '送信スループット', val: parseFloat(txB.value), unit: txB.unit, color: 'var(--color-warning)' }
        ];
        
        fields.forEach(f => {
            const card = document.createElement('div');
            card.className = 'glass-card kpi-card';
            card.style.setProperty('--card-accent', f.color);
            
            card.innerHTML = `
                <span class="kpi-title">${f.label}</span>
                <div class="kpi-value">${formatNumber(f.val, 1)}<span class="kpi-unit">${f.unit}</span></div>
            `;
            list.appendChild(card);
        });
    }
}

// Fetch dashboard data periodically
async function pollDashboard() {
    if (!window.pywebview || !window.pywebview.api || !sourceId) return;
    
    try {
        const source = await window.pywebview.api.get_source(sourceId);
        if (!source) return;
        
        document.getElementById('source-name').innerHTML = `<span class="title-gradient">${source.name}</span>`;
        
        let subTitle = '';
        if (source.type === 'mqtt') subTitle = `MQTT: Broker ${source.config.broker} | Topic ${source.config.topic}`;
        else if (source.type === 'https') subTitle = `HTTPS: ${source.config.url}`;
        else if (source.type === 'file') subTitle = `FILE: ${source.config.filepath}`;
        document.getElementById('source-desc').textContent = subTitle;
        
        const activeDot = document.getElementById('status-dot');
        const activeText = document.getElementById('status-text');
        
        if (source.active) {
            activeDot.className = 'status-dot';
            activeText.textContent = 'リアルタイム同期中';
        } else {
            activeDot.className = 'status-dot offline';
            activeText.textContent = '監視一時停止中';
        }
        
        dataType = source.data_type;
        
        if (dataType === 'environment') {
            document.getElementById('chart-main-title').textContent = '環境センサー 時系列データ';
            const history = await window.pywebview.api.get_environment_history(sourceId, 100);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('environment', history[history.length - 1]);
                initChart('environment', history);
            }
        } else if (dataType === 'traffic') {
            document.getElementById('chart-main-title').textContent = 'ネットワークトラフィック 時系列データ';
            const history = await window.pywebview.api.get_traffic_history(sourceId, 100);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('traffic', history[history.length - 1]);
                initChart('traffic', history);
            }
        } else {
            // Unknown datatype yet
            updateKpiCards('unknown', null);
        }
    } catch(err) {
        console.error("Dashboard polling error:", err);
    }
}

// Start polling
window.addEventListener('pywebviewready', () => {
    pollDashboard();
    // Refresh every 2 seconds
    setInterval(pollDashboard, 2000);
});
