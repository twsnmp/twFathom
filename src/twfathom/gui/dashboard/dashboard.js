let sourceId = null;
let chart = null;
let anomalyChart = null;
let anomalyViewMode = 'tiles'; // 'tiles' or 'chart'
let anomalyEnabled = false;
let dataType = 'unknown';
let lastDataSignature = '';
let lastAnomalySignature = '';

// Parse query params to get source ID
const urlParams = new URLSearchParams(window.location.search);
sourceId = parseInt(urlParams.get('id'), 10);

// Safe localStorage wrapper to prevent crash on platforms with restricted access (e.g., Linux WebKitGTK)
const safeStorage = {
    _data: {},
    getItem(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (e) {
            console.warn("localStorage is not accessible, using in-memory fallback:", e);
            return this._data[key] || null;
        }
    },
    setItem(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch (e) {
            console.warn("localStorage is not accessible, using in-memory fallback:", e);
            this._data[key] = value;
        }
    }
};

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

function formatBytesSize(bytes) {
    if (bytes === null || bytes === undefined || isNaN(bytes)) return { value: '0', unit: 'B' };
    if (bytes < 1024) return { value: bytes.toFixed(1), unit: 'B' };
    if (bytes < 1024 * 1024) return { value: (bytes / 1024).toFixed(1), unit: 'KB' };
    if (bytes < 1024 * 1024 * 1024) return { value: (bytes / (1024 * 1024)).toFixed(1), unit: 'MB' };
    return { value: (bytes / (1024 * 1024 * 1024)).toFixed(1), unit: 'GB' };
}

function formatSpeed(mbPerSec) {
    if (mbPerSec === null || mbPerSec === undefined || isNaN(mbPerSec)) return { value: '0', unit: 'KB/s' };
    const kbPerSec = mbPerSec * 1024;
    if (kbPerSec < 1024) {
        return { value: kbPerSec.toFixed(1), unit: 'KB/s' };
    }
    return { value: mbPerSec.toFixed(2), unit: 'MB/s' };
}

// Initialise ECharts for anomaly score line chart
function initAnomalyChart(data) {
    const chartDom = document.getElementById('anomaly-chart');
    if (!chartDom) return;
    
    let savedZoom = null;
    if (anomalyChart) {
        const currentOption = anomalyChart.getOption();
        if (currentOption && currentOption.dataZoom && currentOption.dataZoom[0]) {
            savedZoom = {
                start: currentOption.dataZoom[0].start,
                end: currentOption.dataZoom[0].end
            };
        }
    }
    
    if (!anomalyChart) {
        anomalyChart = echarts.init(chartDom);
        const resizeObserver = new ResizeObserver(() => {
            if (anomalyChart) anomalyChart.resize();
        });
        resizeObserver.observe(chartDom);
    }
    
    const timestamps = data.timestamps.map(t => {
        try {
            const dt = new Date(t);
            const dateStr = dt.toLocaleDateString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' });
            const timeStr = dt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            return `${dateStr} ${timeStr}`;
        } catch(e) {
            return t;
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
    
    const baseDataZoom = [
        {
            type: 'slider',
            show: true,
            xAxisIndex: [0],
            start: savedZoom ? savedZoom.start : 0,
            end: savedZoom ? savedZoom.end : 100,
            height: 16,
            bottom: 12,
            borderColor: 'rgba(255, 255, 255, 0.08)',
            backgroundColor: 'rgba(255, 255, 255, 0.01)',
            fillerColor: 'rgba(239, 68, 68, 0.08)',
            handleIcon: 'path://M-1.5,0.5c0-0.2,0.1-0.4,0.3-0.5c0.2-0.1,0.4-0.1,0.6,0c0.2,0.1,0.3,0.3,0.3,0.5v15c0,0.2-0.1,0.4-0.3,0.5c-0.2,0.1-0.4,0.1-0.6,0c-0.2-0.1-0.3-0.3-0.3-0.5V0.5z',
            handleSize: '120%',
            handleStyle: {
                color: '#ef4444',
                borderColor: 'rgba(239, 68, 68, 0.4)',
                shadowBlur: 3,
                shadowColor: 'rgba(239, 68, 68, 0.2)'
            },
            moveHandleStyle: {
                color: 'rgba(239, 68, 68, 0.2)'
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
            start: savedZoom ? savedZoom.start : 0,
            end: savedZoom ? savedZoom.end : 100,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true
        }
    ];
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: baseTooltip,
        grid: baseGrid,
        dataZoom: baseDataZoom,
        xAxis: {
            type: 'category',
            boundaryGap: data.scores.length <= 1,
            data: timestamps,
            axisLabel: { 
                color: '#9ca3af',
                formatter: function(value) {
                    return value && value.includes(' ') ? value.split(' ')[1] : value;
                }
            },
            axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
        },
        yAxis: {
            type: 'value',
            name: '異常度スコア',
            scale: true,
            axisLabel: { color: '#9ca3af' },
            splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
        },
        series: [
            {
                name: '異常度',
                type: 'line',
                smooth: true,
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 6,
                data: data.scores,
                itemStyle: { color: '#ef4444' },
                lineStyle: { width: 3 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(239, 68, 68, 0.15)' },
                        { offset: 1, color: 'rgba(239, 68, 68, 0)' }
                    ])
                },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    label: {
                        position: 'end',
                        color: '#9ca3af',
                        fontSize: 10
                    },
                    data: [
                        {
                            yAxis: 3.84,
                            name: '注意 (3.84)',
                            lineStyle: {
                                color: 'rgba(245, 158, 11, 0.5)',
                                type: 'dashed',
                                width: 1.5
                            }
                        },
                        {
                            yAxis: 6.63,
                            name: '異常 (6.63)',
                            lineStyle: {
                                color: 'rgba(239, 68, 68, 0.5)',
                                type: 'dashed',
                                width: 1.5
                            }
                        }
                    ]
                }
            }
        ]
    };
    
    anomalyChart.setOption(option, true);
}



// Build GitHub-style colored history tiles for past anomaly scores
function updateAnomalyHistoryGrid(anomalyResult) {
    const gridDom = document.getElementById('anomaly-history-grid');
    const titleDom = document.getElementById('anomaly-history-title');
    const tooltip = document.getElementById('anomaly-grid-tooltip');
    if (!gridDom) return;
    
    gridDom.innerHTML = '';
    
    const scores = anomalyResult.scores || [];
    const timestamps = anomalyResult.timestamps || [];
    
    // Calculate display limit dynamically to fit exactly based on grid container width and height
    const gridWidth = gridDom.getBoundingClientRect().width || gridDom.clientWidth || 500;
    const gridHeight = gridDom.getBoundingClientRect().height || gridDom.clientHeight || 80;
    const padding = 16; // 8px left + 8px right padding
    const itemWidth = 10;
    const itemHeight = 14;
    const gap = 3;
    
    // Number of items that can fit in a single row
    const itemsPerRow = Math.floor((gridWidth - padding + gap) / (itemWidth + gap)) || 30;
    // Number of rows that can fit vertically (subtract padding)
    const rowsCount = Math.floor((gridHeight - padding + gap) / (itemHeight + gap)) || 2;
    // Enforce at least 2 rows
    const finalRows = Math.max(2, rowsCount);
    
    const displayLimit = itemsPerRow * finalRows;
    
    if (titleDom) {
        titleDom.textContent = `判定履歴 (直近${displayLimit}件)`;
    }
    
    const startIdx = Math.max(0, scores.length - displayLimit);
    
    for (let i = startIdx; i < scores.length; i++) {
        const score = scores[i];
        const ts = timestamps[i];
        
        let status = 'normal';
        let color = 'rgba(16, 185, 129, 0.25)'; // Normal (translucent green)
        let border = '1px solid rgba(16, 185, 129, 0.4)';
        
        if (score > 6.63) {
            status = 'critical';
            color = 'rgba(239, 68, 68, 0.9)'; // Critical (red)
            border = '1px solid #ef4444';
        } else if (score > 3.84) {
            status = 'warning';
            color = 'rgba(245, 158, 11, 0.8)'; // Warning (yellow)
            border = '1px solid var(--color-warning)';
        }
        
        // Format timestamp to readable Japanese local format
        let timeStr = ts;
        try {
            const dt = new Date(ts);
            timeStr = dt.toLocaleString('ja-JP');
        } catch(e) {}
        
        const tile = document.createElement('div');
        tile.style.width = '10px';
        tile.style.height = '14px';
        tile.style.backgroundColor = color;
        tile.style.border = border;
        tile.style.borderRadius = '2px';
        tile.style.cursor = 'pointer';
        
        // Hover micro-animations
        tile.style.transition = 'all 0.1s ease';
        
        tile.addEventListener('mouseenter', () => {
            tile.style.transform = 'scale(1.2)';
            tile.style.zIndex = '10';
            if (status === 'normal') {
                tile.style.backgroundColor = 'rgba(16, 185, 129, 0.8)';
            }
        });
        
        tile.addEventListener('mousemove', (e) => {
            if (tooltip) {
                tooltip.style.display = 'block';
                // Position tooltip slightly offset from cursor
                tooltip.style.left = (e.clientX + 12) + 'px';
                tooltip.style.top = (e.clientY + 12) + 'px';
                
                let scoreText = score.toFixed(2);
                let statusBadge = '';
                if (status === 'critical') {
                    statusBadge = '<span style="color: #ef4444; font-weight: bold; margin-left: 6px;">[異常]</span>';
                } else if (status === 'warning') {
                    statusBadge = '<span style="color: var(--color-warning); font-weight: bold; margin-left: 6px;">[注意]</span>';
                } else {
                    statusBadge = '<span style="color: var(--color-success); font-weight: bold; margin-left: 6px;">[正常]</span>';
                }
                
                tooltip.innerHTML = `
                    <div style="margin-bottom: 4px;"><strong>日時:</strong> ${timeStr}</div>
                    <div><strong>異常度:</strong> ${scoreText}${statusBadge}</div>
                `;
            }
        });
        
        tile.addEventListener('mouseleave', () => {
            tile.style.transform = 'scale(1)';
            tile.style.zIndex = '1';
            tile.style.backgroundColor = color;
            if (tooltip) {
                tooltip.style.display = 'none';
            }
        });
        
        gridDom.appendChild(tile);
    }
    
    if (scores.length === 0) {
        gridDom.innerHTML = '<div style="font-size: 11px; color: var(--text-muted); width: 100%; text-align: center;">履歴データがありません</div>';
    }
}

// Setup anomaly view mode selector (tiles vs chart)
function setupAnomalyViewMode() {
    const btnTiles = document.getElementById('btn-view-tiles');
    const btnChart = document.getElementById('btn-view-chart');
    if (!btnTiles || !btnChart) return;
    
    const savedMode = safeStorage.getItem(`anomaly_view_mode_${sourceId}`);
    anomalyViewMode = savedMode || 'tiles';
    
    const updateViewUI = () => {
        const viewTiles = document.getElementById('anomaly-tiles-view');
        const viewChart = document.getElementById('anomaly-chart-view');
        
        if (anomalyViewMode === 'tiles') {
            btnTiles.classList.add('active');
            btnChart.classList.remove('active');
            if (viewTiles) viewTiles.style.display = 'flex';
            if (viewChart) viewChart.style.display = 'none';
        } else {
            btnTiles.classList.remove('active');
            btnChart.classList.add('active');
            if (viewTiles) viewTiles.style.display = 'none';
            if (viewChart) viewChart.style.display = 'block';
            
            // Force ECharts reflow when showing chart view
            setTimeout(() => {
                if (anomalyChart) anomalyChart.resize();
            }, 50);
        }
    };
    
    updateViewUI();
    
    btnTiles.addEventListener('click', () => {
        anomalyViewMode = 'tiles';
        safeStorage.setItem(`anomaly_view_mode_${sourceId}`, 'tiles');
        updateViewUI();
        pollDashboard();
    });
    
    btnChart.addEventListener('click', () => {
        anomalyViewMode = 'chart';
        safeStorage.setItem(`anomaly_view_mode_${sourceId}`, 'chart');
        updateViewUI();
        pollDashboard();
    });
}

// Setup anomaly button behavior and state persistence
function setupAnomalyToggle() {
    const btn = document.getElementById('btn-anomaly');
    if (!btn) return;
    
    // Load state from localStorage
    const saved = safeStorage.getItem(`anomaly_enabled_${sourceId}`);
    anomalyEnabled = (saved === 'true');
    
    const updateButtonUI = () => {
        const mainChartContainer = document.getElementById('main-chart-container');
        if (anomalyEnabled) {
            btn.classList.add('active');
            btn.style.background = 'var(--color-primary-gradient)';
            btn.style.color = '#050508';
            btn.style.boxShadow = '0 2px 8px rgba(0, 210, 255, 0.2)';
            const svg = btn.querySelector('svg');
            if (svg) svg.style.color = '#050508';
            
            if (mainChartContainer) mainChartContainer.style.display = 'none';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'rgba(255, 255, 255, 0.04)';
            btn.style.color = 'var(--text-secondary)';
            btn.style.boxShadow = 'none';
            const svg = btn.querySelector('svg');
            if (svg) svg.style.color = 'var(--text-secondary)';
            
            if (mainChartContainer) mainChartContainer.style.display = 'flex';
            // Force main chart reflow
            lastDataSignature = ''; // Force redraw on next poll
            setTimeout(() => {
                if (chart) chart.resize();
            }, 100);
        }
    };
    
    updateButtonUI();
    
    btn.addEventListener('click', () => {
        anomalyEnabled = !anomalyEnabled;
        safeStorage.setItem(`anomaly_enabled_${sourceId}`, anomalyEnabled);
        updateButtonUI();
        // Immediately trigger poll to update visual state
        pollDashboard();
    });
}

// Initialise ECharts with premium dark theme configuration
function initChart(type, data) {
    const chartDom = document.getElementById('main-chart');
    if (!chartDom) return;
    
    const controlsDom = document.getElementById('chart-controls');
    if (controlsDom) controlsDom.innerHTML = '';
    
    let savedZoom = null;
    let savedLegend = {};
    
    // Load from localStorage
    try {
        const savedStr = safeStorage.getItem(`legend_selected_${sourceId}_${dataType}`);
        if (savedStr) {
            savedLegend = JSON.parse(savedStr);
        }
    } catch (e) {
        console.error("Error loading legend selection:", e);
    }
    
    if (chart) {
        const currentOption = chart.getOption();
        if (currentOption) {
            // Maintain runtime legend selection
            if (currentOption.legend && currentOption.legend[0] && currentOption.legend[0].selected) {
                savedLegend = Object.assign({}, savedLegend, currentOption.legend[0].selected);
            }
            // Maintain runtime zoom level
            if (currentOption.dataZoom && currentOption.dataZoom[0]) {
                savedZoom = {
                    start: currentOption.dataZoom[0].start,
                    end: currentOption.dataZoom[0].end
                };
            }
        }
    }

    if (!chart) {
        chart = echarts.init(chartDom);
        // Make responsive using ResizeObserver
        const resizeObserver = new ResizeObserver(() => {
            if (chart) chart.resize();
        });
        resizeObserver.observe(chartDom);
        
        // Listen to legend selection changes and persist them
        chart.on('legendselectchanged', (params) => {
            try {
                safeStorage.setItem(`legend_selected_${sourceId}_${dataType}`, JSON.stringify(params.selected));
            } catch (e) {
                console.error("Error saving legend selection:", e);
            }
        });
    }
    
    let option = {};
    const timestamps = data.map(d => {
        // Parse ISO timestamp to readable date and time
        try {
            const dt = new Date(d.timestamp);
            const dateStr = dt.toLocaleDateString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' });
            const timeStr = dt.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            return `${dateStr} ${timeStr}`;
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
    
    // Zoom should cover all data by default (0-100), unless zoom state was saved during redraws
    const baseDataZoom = [
        {
            type: 'slider',
            show: true,
            xAxisIndex: [0],
            start: savedZoom ? savedZoom.start : 0,
            end: savedZoom ? savedZoom.end : 100,
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
            start: savedZoom ? savedZoom.start : 0,
            end: savedZoom ? savedZoom.end : 100,
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

        const otherKeys = ['soil_moisture', 'pressure', 'co2', 'illuminance'];
        const availableKeys = otherKeys.filter(key => data.some(d => d[key] !== null && d[key] !== undefined));
        
        let activeOtherKey = safeStorage.getItem(`active_right_axis_${sourceId}`);
        if (!activeOtherKey || !availableKeys.includes(activeOtherKey)) {
            activeOtherKey = availableKeys[0] || null;
        }

        // Render pill selector in header
        const controlsDom = document.getElementById('chart-controls');
        if (controlsDom) {
            if (availableKeys.length > 1) {
                let pillsHtml = '<div class="pill-selector">';
                availableKeys.forEach(key => {
                    const isActive = (key === activeOtherKey);
                    const label = ENV_FIELDS[key].name.split(' ')[0];
                    pillsHtml += `<button class="pill-btn${isActive ? ' active' : ''}" data-key="${key}">${label}</button>`;
                });
                pillsHtml += '</div>';
                controlsDom.innerHTML = pillsHtml;
                
                // Add event listeners to buttons
                controlsDom.querySelectorAll('.pill-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const selectedKey = e.target.getAttribute('data-key');
                        safeStorage.setItem(`active_right_axis_${sourceId}`, selectedKey);
                        lastDataSignature = ''; // Reset signature to force redraw
                        pollDashboard();
                    });
                });
            } else {
                controlsDom.innerHTML = '';
            }
        }

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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ];

            seriesConfig = [
                {
                    name: ENV_FIELDS.temperature.name,
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                selected: savedLegend,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: data.length <= 1,
                data: timestamps,
                axisLabel: { 
                    color: '#9ca3af',
                    formatter: function(value) {
                        return value && value.includes(' ') ? value.split(' ')[1] : value;
                    }
                },
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
                selected: savedLegend,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: data.length <= 1,
                data: timestamps,
                axisLabel: { 
                    color: '#9ca3af',
                    formatter: function(value) {
                        return value && value.includes(' ') ? value.split(' ')[1] : value;
                    }
                },
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
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
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    yAxisIndex: 1,
                    data: rxBPS,
                    itemStyle: { color: '#00f5d4' },
                    lineStyle: { width: 2, type: 'dashed' }
                },
                {
                    name: '送信速度 (bps)',
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    yAxisIndex: 1,
                    data: txBPS,
                    itemStyle: { color: '#f59e0b' },
                    lineStyle: { width: 2, type: 'dashed' }
                }
            ]
        };
    } else if (type === 'cpu_mem_disk') {
        const cpuData = data.map(d => d.cpu);
        const memData = data.map(d => d.memory);
        const diskData = data.map(d => d.disk);
        const hasDisk = data.some(d => d.disk !== null && d.disk !== undefined);
        
        const legendData = ['CPU使用率 (%)', 'メモリ使用率 (%)'];
        if (hasDisk) legendData.push('ディスク使用率 (%)');
        
        const seriesConfig = [
            {
                name: 'CPU使用率 (%)',
                type: 'line',
                smooth: true,
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 6,
                data: cpuData,
                itemStyle: { color: '#ef4444' },
                lineStyle: { width: 3 },
                yAxisIndex: 0,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(239, 68, 68, 0.15)' },
                        { offset: 1, color: 'rgba(239, 68, 68, 0)' }
                    ])
                }
            },
            {
                name: 'メモリ使用率 (%)',
                type: 'line',
                smooth: true,
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 6,
                data: memData,
                itemStyle: { color: '#00d2ff' },
                lineStyle: { width: 3 },
                yAxisIndex: 1,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(0, 210, 255, 0.15)' },
                        { offset: 1, color: 'rgba(0, 210, 255, 0)' }
                    ])
                }
            }
        ];
        
        if (hasDisk) {
            seriesConfig.push({
                name: 'ディスク使用率 (%)',
                type: 'line',
                smooth: true,
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 6,
                data: diskData,
                itemStyle: { color: '#10b981' },
                lineStyle: { width: 3 },
                yAxisIndex: 1,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(16, 185, 129, 0.15)' },
                        { offset: 1, color: 'rgba(16, 185, 129, 0)' }
                    ])
                }
            });
        }
        
        option = {
            backgroundColor: 'transparent',
            tooltip: baseTooltip,
            legend: {
                data: legendData,
                selected: savedLegend,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: data.length <= 1,
                data: timestamps,
                axisLabel: { 
                    color: '#9ca3af',
                    formatter: function(value) {
                        return value && value.includes(' ') ? value.split(' ')[1] : value;
                    }
                },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: [
                {
                    type: 'value',
                    name: 'CPU使用率 (%)',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: 'メモリ/ディスク (%)',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ],
            series: seriesConfig
        };
    } else if (type === 'process_load') {
        const processData = data.map(d => d.process);
        const loadData = data.map(d => d.load);
        
        option = {
            backgroundColor: 'transparent',
            tooltip: baseTooltip,
            legend: {
                data: ['プロセス数 (個)', 'システム負荷 (Load)'],
                selected: savedLegend,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: data.length <= 1,
                data: timestamps,
                axisLabel: { 
                    color: '#9ca3af',
                    formatter: function(value) {
                        return value && value.includes(' ') ? value.split(' ')[1] : value;
                    }
                },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: [
                {
                    type: 'value',
                    name: 'プロセス数',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: 'システム負荷',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ],
            series: [
                {
                    name: 'プロセス数 (個)',
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    data: processData,
                    itemStyle: { color: '#bd00ff' },
                    lineStyle: { width: 3 },
                    yAxisIndex: 0,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(189, 0, 255, 0.15)' },
                            { offset: 1, color: 'rgba(189, 0, 255, 0)' }
                        ])
                    }
                },
                {
                    name: 'システム負荷 (Load)',
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    data: loadData,
                    itemStyle: { color: '#f59e0b' },
                    lineStyle: { width: 3 },
                    yAxisIndex: 1,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(245, 158, 11, 0.15)' },
                            { offset: 1, color: 'rgba(245, 158, 11, 0)' }
                        ])
                    }
                }
            ]
        };
    } else if (type === 'network_speed') {
        const txSpeed = data.map(d => d.tx_speed);
        const rxSpeed = data.map(d => d.rx_speed);
        
        option = {
            backgroundColor: 'transparent',
            tooltip: baseTooltip,
            legend: {
                data: ['送信速度 (MB/s)', '受信速度 (MB/s)'],
                selected: savedLegend,
                textStyle: { color: '#9ca3af', fontFamily: 'Inter' }
            },
            grid: baseGrid,
            dataZoom: baseDataZoom,
            xAxis: {
                type: 'category',
                boundaryGap: data.length <= 1,
                data: timestamps,
                axisLabel: { 
                    color: '#9ca3af',
                    formatter: function(value) {
                        return value && value.includes(' ') ? value.split(' ')[1] : value;
                    }
                },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: [
                {
                    type: 'value',
                    name: '送信速度 (MB/s)',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                {
                    type: 'value',
                    name: '受信速度 (MB/s)',
                    scale: true,
                    axisLabel: { color: '#9ca3af' },
                    splitLine: { show: false }
                }
            ],
            series: [
                {
                    name: '送信速度 (MB/s)',
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    data: txSpeed,
                    itemStyle: { color: '#bd00ff' },
                    lineStyle: { width: 3 },
                    yAxisIndex: 0,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(189, 0, 255, 0.15)' },
                            { offset: 1, color: 'rgba(189, 0, 255, 0)' }
                        ])
                    }
                },
                {
                    name: '受信速度 (MB/s)',
                    type: 'line',
                    smooth: true,
                    showSymbol: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    data: rxSpeed,
                    itemStyle: { color: '#00f5d4' },
                    lineStyle: { width: 3 },
                    yAxisIndex: 1,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(0, 245, 212, 0.15)' },
                            { offset: 1, color: 'rgba(0, 245, 212, 0)' }
                        ])
                    }
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
    } else if (type === 'cpu_mem_disk') {
        const fields = [
            { label: 'CPU 使用率', val: latestData.cpu, unit: '%', color: '#ef4444' },
            { label: 'メモリ使用率', val: latestData.memory, unit: '%', color: '#00d2ff' }
        ];
        
        if (latestData.disk !== null && latestData.disk !== undefined) {
            fields.push({ label: 'ディスク使用率', val: latestData.disk, unit: '%', color: '#10b981' });
        }
        
        fields.forEach(f => {
            if (f.val === null || f.val === undefined) return;
            
            const card = document.createElement('div');
            card.className = 'glass-card kpi-card';
            card.style.setProperty('--card-accent', f.color);
            
            card.innerHTML = `
                <span class="kpi-title">${f.label}</span>
                <div class="kpi-value">${formatNumber(f.val, 1)}<span class="kpi-unit">${f.unit}</span></div>
            `;
            list.appendChild(card);
        });
    } else if (type === 'process_load') {
        const fields = [
            { label: 'プロセス数', val: latestData.process, unit: '個', color: '#bd00ff', isInteger: true },
            { label: 'システム負荷', val: latestData.load, unit: 'Load', color: '#f59e0b', isInteger: false }
        ];
        
        fields.forEach(f => {
            if (f.val === null || f.val === undefined) return;
            
            const card = document.createElement('div');
            card.className = 'glass-card kpi-card';
            card.style.setProperty('--card-accent', f.color);
            
            card.innerHTML = `
                <span class="kpi-title">${f.label}</span>
                <div class="kpi-value">${f.isInteger ? f.val : formatNumber(f.val, 2)}<span class="kpi-unit">${f.unit}</span></div>
            `;
            list.appendChild(card);
        });
    } else if (type === 'network_speed') {
        const txSp = formatSpeed(latestData.tx_speed);
        const rxSp = formatSpeed(latestData.rx_speed);
        const txBytes = formatBytesSize(latestData.sent);
        const rxBytes = formatBytesSize(latestData.recv);
        
        const fields = [
            { label: '送信速度', val: parseFloat(txSp.value), unit: txSp.unit, color: '#bd00ff', decimals: txSp.unit === 'KB/s' ? 1 : 2 },
            { label: '受信速度', val: parseFloat(rxSp.value), unit: rxSp.unit, color: '#00f5d4', decimals: rxSp.unit === 'KB/s' ? 1 : 2 },
            { label: '送信データ量', val: parseFloat(txBytes.value), unit: txBytes.unit, color: '#e0aaff', decimals: 1 },
            { label: '受信データ量', val: parseFloat(rxBytes.value), unit: rxBytes.unit, color: '#c8b6ff', decimals: 1 }
        ];
        
        fields.forEach(f => {
            if (f.val === null || f.val === undefined || isNaN(f.val)) return;
            
            const card = document.createElement('div');
            card.className = 'glass-card kpi-card';
            card.style.setProperty('--card-accent', f.color);
            
            card.innerHTML = `
                <span class="kpi-title">${f.label}</span>
                <div class="kpi-value">${formatNumber(f.val, f.decimals)}<span class="kpi-unit">${f.unit}</span></div>
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
        const titlebarTitle = document.getElementById('titlebar-window-title');
        if (titlebarTitle) {
            titlebarTitle.textContent = `${source.name} - ダッシュボード`;
        }
        
        let subTitle = '';
        if (source.type === 'mqtt') subTitle = `MQTT: Broker ${source.config.broker} | Topic ${source.config.topic}`;
        else if (source.type === 'https') subTitle = `HTTPS: ${source.config.url}`;
        else if (source.type === 'file') subTitle = `FILE: ${source.config.filepath}`;
        document.getElementById('source-desc').textContent = subTitle;
        
        const activeDot = document.getElementById('status-dot');
        const activeText = document.getElementById('status-text');
        
        if (source.active) {
            activeDot.className = 'status-dot';
            activeText.textContent = '同期中';
        } else {
            activeDot.className = 'status-dot offline';
            activeText.textContent = '停止中';
        }
        
        dataType = source.data_type;
        
        if (dataType === 'environment') {
            document.getElementById('chart-main-title').textContent = '環境センサー 時系列データ';
            const history = await window.pywebview.api.get_environment_history(sourceId, -1);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('environment', history[history.length - 1]);
                if (!anomalyEnabled) {
                    initChart('environment', history);
                }
            }
        } else if (dataType === 'traffic') {
            document.getElementById('chart-main-title').textContent = 'ネットワークトラフィック 時系列データ';
            const history = await window.pywebview.api.get_traffic_history(sourceId, -1);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('traffic', history[history.length - 1]);
                if (!anomalyEnabled) {
                    initChart('traffic', history);
                }
            }
        } else if (dataType === 'cpu_mem_disk') {
            document.getElementById('chart-main-title').textContent = 'システムリソース 時系列データ';
            const history = await window.pywebview.api.get_cpu_mem_disk_history(sourceId, -1);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('cpu_mem_disk', history[history.length - 1]);
                if (!anomalyEnabled) {
                    initChart('cpu_mem_disk', history);
                }
            }
        } else if (dataType === 'process_load') {
            document.getElementById('chart-main-title').textContent = 'システム負荷・プロセス 時系列データ';
            const history = await window.pywebview.api.get_process_load_history(sourceId, -1);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('process_load', history[history.length - 1]);
                if (!anomalyEnabled) {
                    initChart('process_load', history);
                }
            }
        } else if (dataType === 'network_speed') {
            document.getElementById('chart-main-title').textContent = 'ネットワーク通信速度 時系列データ';
            const history = await window.pywebview.api.get_network_speed_history(sourceId, -1);
            
            const signature = history.length > 0 ? `${history.length}_${history[history.length - 1].timestamp}` : 'empty';
            if (signature !== lastDataSignature) {
                lastDataSignature = signature;
                updateKpiCards('network_speed', history[history.length - 1]);
                if (!anomalyEnabled) {
                    initChart('network_speed', history);
                }
            }
        } else {
            // Unknown datatype yet
            updateKpiCards('unknown', null);
        }

        // 異常検知表示の制御
        const anomalyContainer = document.getElementById('anomaly-container');
        if (anomalyContainer) {
            if (anomalyEnabled) {
                anomalyContainer.style.display = 'flex';
                // APIから異常検知結果を取得
                const anomalyResult = await window.pywebview.api.run_anomaly_detection(sourceId);
                
                if (anomalyResult && anomalyResult.status !== 'error') {
                    // 最新の状態を更新
                    const badge = document.getElementById('anomaly-status-badge');
                    const dot = document.getElementById('anomaly-status-dot');
                    const text = document.getElementById('anomaly-status-text');
                    const detailMsg = document.getElementById('anomaly-detail-message');
                    const detailSub = document.getElementById('anomaly-detail-sub');
                    
                    if (badge && dot && text) {
                        text.textContent = anomalyResult.status_ja;
                        if (anomalyResult.status === 'critical') {
                            badge.style.background = 'rgba(239, 68, 68, 0.1)';
                            badge.style.borderColor = 'rgba(239, 68, 68, 0.2)';
                            badge.style.color = '#ef4444';
                            dot.style.background = '#ef4444';
                            dot.style.boxShadow = '0 0 8px #ef4444';
                        } else if (anomalyResult.status === 'warning') {
                            badge.style.background = 'rgba(245, 158, 11, 0.1)';
                            badge.style.borderColor = 'rgba(245, 158, 11, 0.2)';
                            badge.style.color = 'var(--color-warning)';
                            dot.style.background = 'var(--color-warning)';
                            dot.style.boxShadow = '0 0 8px var(--color-warning)';
                        } else {
                            badge.style.background = 'rgba(16, 185, 129, 0.1)';
                            badge.style.borderColor = 'rgba(16, 185, 129, 0.2)';
                            badge.style.color = 'var(--color-success)';
                            dot.style.background = 'var(--color-success)';
                            dot.style.boxShadow = '0 0 8px var(--color-success)';
                        }
                    }
                    
                    if (detailMsg) detailMsg.textContent = anomalyResult.message;
                    if (detailSub) {
                        if (anomalyResult.latest_detail && anomalyResult.latest_detail.val !== null) {
                            detailSub.textContent = `現在値: ${anomalyResult.latest_detail.val.toFixed(2)}`;
                        } else {
                            detailSub.textContent = '';
                        }
                    }
                    
                    // 判定履歴または折れ線グラフの描画
                    if (anomalyResult.scores && anomalyResult.scores.length > 0) {
                        if (anomalyViewMode === 'tiles') {
                            updateAnomalyHistoryGrid(anomalyResult);
                        } else {
                            const sig = `${anomalyResult.scores.length}_${anomalyResult.timestamps[anomalyResult.timestamps.length - 1]}`;
                            if (sig !== lastAnomalySignature) {
                                lastAnomalySignature = sig;
                                initAnomalyChart(anomalyResult);
                            }
                        }
                    }
                } else {
                    document.getElementById('anomaly-detail-message').textContent = anomalyResult ? anomalyResult.message : '異常検知APIの取得に失敗しました';
                }
            } else {
                anomalyContainer.style.display = 'none';
            }
        }
    } catch(err) {
        console.error("Dashboard polling error:", err);
    }
}

// Window control actions
function closeDashboardWindow() {
    if (window.pywebview && window.pywebview.api && sourceId) {
        window.pywebview.api.close_dashboard(sourceId);
    }
}

// Minimize window
function minimizeDashboardWindow() {
    if (window.pywebview && window.pywebview.api && sourceId) {
        window.pywebview.api.minimize_dashboard(sourceId);
    }
}

// Window resizing logic
function setupWindowResize() {
    const handleR = document.getElementById('resize-r');
    const handleB = document.getElementById('resize-b');
    const handleBR = document.getElementById('resize-br');
    
    if (!handleR || !handleB || !handleBR) return;
    
    let isResizing = false;
    let resizeType = ''; // 'r', 'b', 'br'
    let startMouseX, startMouseY, startWidth, startHeight;
    let currentWidth, currentHeight;
    let resizePending = false;
    
    const startResize = (e, type) => {
        isResizing = true;
        resizeType = type;
        startMouseX = e.screenX;
        startMouseY = e.screenY;
        startWidth = window.outerWidth;
        startHeight = window.outerHeight;
        currentWidth = startWidth;
        currentHeight = startHeight;
        
        e.preventDefault();
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    };
    
    handleR.addEventListener('mousedown', (e) => startResize(e, 'r'));
    handleB.addEventListener('mousedown', (e) => startResize(e, 'b'));
    handleBR.addEventListener('mousedown', (e) => startResize(e, 'br'));
    
    function onMouseMove(e) {
        if (!isResizing) return;
        const dx = e.screenX - startMouseX;
        const dy = e.screenY - startMouseY;
        
        if (resizeType === 'r' || resizeType === 'br') {
            currentWidth = Math.max(450, startWidth + dx);
        }
        if (resizeType === 'b' || resizeType === 'br') {
            currentHeight = Math.max(350, startHeight + dy);
        }
        
        if (!resizePending) {
            resizePending = true;
            requestAnimationFrame(() => {
                if (window.pywebview && window.pywebview.api && sourceId) {
                    window.pywebview.api.resize_dashboard(sourceId, currentWidth, currentHeight);
                }
                if (chart) chart.resize();
                if (anomalyChart && anomalyViewMode === 'chart') anomalyChart.resize();
                if (anomalyEnabled && anomalyViewMode === 'tiles') pollDashboard();
                resizePending = false;
            });
        }
    }
    
    function onMouseUp() {
        isResizing = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    }
}

// Initial Loading
function initDashboard() {
    setupAnomalyViewMode();
    setupAnomalyToggle();
    pollDashboard();
    // Refresh every 2 seconds
    setInterval(pollDashboard, 2000);
    
    // Recalculate tiles grid dynamically on window resize
    window.addEventListener('resize', () => {
        if (anomalyEnabled && anomalyViewMode === 'tiles') {
            pollDashboard();
        }
    });
    
    setupWindowResize();
    setupWindowDrag();
}

if (window.pywebview && window.pywebview.api) {
    initDashboard();
} else {
    window.addEventListener('pywebviewready', initDashboard);
}

// Custom JS window dragging for Linux WebKitGTK where easy_drag/drag-region is not natively supported or buggy
function setupWindowDrag() {
    const isLinux = navigator.userAgent.toLowerCase().includes('linux');
    if (!isLinux) return;

    const dragRegion = document.querySelector('.pywebview-drag-region');
    if (!dragRegion) return;

    let isDragging = false;
    let startMouseX = 0;
    let startMouseY = 0;
    let startWinX = 0;
    let startWinY = 0;
    let currentX = 0;
    let currentY = 0;
    let dragPending = false;

    dragRegion.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Left click only
        if (e.target.closest('button') || e.target.closest('.status-pill') || e.target.closest('a')) {
            return; // Ignore button and link clicks
        }

        isDragging = true;
        startMouseX = e.screenX;
        startMouseY = e.screenY;

        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_window_position_from_db(sourceId).then(pos => {
                if (!isDragging) return;
                startWinX = pos.x;
                startWinY = pos.y;
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }
    });

    function onMouseMove(e) {
        if (!isDragging) return;
        const dx = e.screenX - startMouseX;
        const dy = e.screenY - startMouseY;

        currentX = startWinX + dx;
        currentY = startWinY + dy;

        if (!dragPending) {
            dragPending = true;
            requestAnimationFrame(() => {
                if (window.pywebview && window.pywebview.api) {
                    window.pywebview.api.move_dashboard(sourceId, currentX, currentY);
                }
                dragPending = false;
            });
        }
    }

    function onMouseUp() {
        isDragging = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    }
}

