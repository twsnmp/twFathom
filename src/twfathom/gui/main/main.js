const modal = document.getElementById('source-modal');
const form = document.getElementById('source-form');
const formSourceId = document.getElementById('form-source-id');
const modalTitle = document.getElementById('modal-title');

function openAddModal() {
    form.reset();
    formSourceId.value = '';
    modalTitle.textContent = '新規ソース登録';
    document.getElementById('form-type').value = 'mqtt';
    document.getElementById('form-data-type').value = 'unknown';
    handleTypeChange();
    modal.style.display = 'flex';
}

function openEditModal(id, name, type, configStr, interval, dataType) {
    modalTitle.textContent = 'ソースの編集';
    formSourceId.value = id;
    document.getElementById('form-name').value = name;
    document.getElementById('form-type').value = type;
    document.getElementById('form-interval').value = interval;
    document.getElementById('form-data-type').value = dataType || 'unknown';
    
    handleTypeChange();
    
    const config = JSON.parse(configStr);
    
    if (type === 'mqtt') {
        document.getElementById('mqtt-broker').value = config.broker || '';
        document.getElementById('mqtt-port').value = config.port || 1883;
        document.getElementById('mqtt-topic').value = config.topic || '';
        document.getElementById('mqtt-username').value = config.username || '';
        document.getElementById('mqtt-password').value = config.password || '';
    } else if (type === 'https') {
        document.getElementById('https-url').value = config.url || '';
        document.getElementById('https-method').value = config.method || 'GET';
        document.getElementById('https-headers').value = config.headers ? JSON.stringify(config.headers) : '';
        document.getElementById('https-params').value = config.params ? JSON.stringify(config.params) : '';
    } else if (type === 'file') {
        document.getElementById('file-path').value = config.filepath || '';
    }
    
    modal.style.display = 'flex';
}

function closeModal() {
    modal.style.display = 'none';
}

function handleTypeChange() {
    const selectedType = document.getElementById('form-type').value;
    
    // Hide all
    document.querySelectorAll('.type-config').forEach(el => {
        el.style.display = 'none';
    });
    
    // Show selected
    const targetConfig = document.getElementById(`config-${selectedType}`);
    if (targetConfig) {
        targetConfig.style.display = 'block';
    }
}

// Save or Update Source
async function saveSource(event) {
    event.preventDefault();
    
    const id = formSourceId.value;
    const name = document.getElementById('form-name').value;
    const type = document.getElementById('form-type').value;
    const interval = parseInt(document.getElementById('form-interval').value, 10);
    const dataType = document.getElementById('form-data-type').value;
    
    let config = {};
    
    if (type === 'mqtt') {
        config = {
            broker: document.getElementById('mqtt-broker').value,
            port: parseInt(document.getElementById('mqtt-port').value, 10) || 1883,
            topic: document.getElementById('mqtt-topic').value,
            username: document.getElementById('mqtt-username').value,
            password: document.getElementById('mqtt-password').value
        };
    } else if (type === 'https') {
        let headers = {};
        let params = {};
        
        try {
            const hVal = document.getElementById('https-headers').value.trim();
            if (hVal) headers = JSON.parse(hVal);
        } catch (e) {
            alert("ヘッダーのJSON形式が不正です。");
            return;
        }
        
        try {
            const pVal = document.getElementById('https-params').value.trim();
            if (pVal) params = JSON.parse(pVal);
        } catch (e) {
            alert("POSTパラメータのJSON形式が不正です。");
            return;
        }
        
        config = {
            url: document.getElementById('https-url').value,
            method: document.getElementById('https-method').value,
            headers: headers,
            params: params
        };
    } else if (type === 'file') {
        config = {
            filepath: document.getElementById('file-path').value
        };
    }
    
    try {
        if (id) {
            // Update
            const source = await window.pywebview.api.get_source(parseInt(id, 10));
            await window.pywebview.api.update_source(
                parseInt(id, 10),
                name,
                type,
                config,
                interval,
                dataType,
                source.active
            );
        } else {
            // Add
            await window.pywebview.api.add_source(name, type, config, interval, dataType);
        }
        
        closeModal();
        loadSources();
    } catch (err) {
        console.error("Failed to save source:", err);
        alert("保存中にエラーが発生しました。\n" + err);
    }
}

// Load and render sources
async function loadSources() {
    if (!window.pywebview || !window.pywebview.api) return;
    
    try {
        const sources = await window.pywebview.api.get_sources();
        const openDashboards = await window.pywebview.api.get_open_dashboards();
        const tbody = document.getElementById('source-list');
        const noDataMsg = document.getElementById('no-data-msg');
        
        tbody.innerHTML = '';
        
        if (sources.length === 0) {
            noDataMsg.style.display = 'block';
            return;
        }
        
        noDataMsg.style.display = 'none';
        
        sources.forEach(src => {
            const tr = document.createElement('tr');
            
            // Map types to display labels
            const typeLabel = src.type.toUpperCase();
            
            // Map detected data types
            let dataTypeLabel = '未判定';
            if (src.data_type === 'environment') dataTypeLabel = '環境データ';
            else if (src.data_type === 'traffic') dataTypeLabel = 'トラフィック';
            else if (src.data_type === 'cpu_mem_disk') dataTypeLabel = 'CPU・メモリ・ディスク';
            else if (src.data_type === 'process_load') dataTypeLabel = 'プロセス・負荷';
            else if (src.data_type === 'network_speed') dataTypeLabel = '通信スピード';
            
            const activeBadgeClass = src.active ? 'badge-active' : 'badge-paused';
            const activeText = src.active ? '監視中' : '一時停止';
            
            // Safe JSON config for onclick injection
            const safeConfig = JSON.stringify(src.config).replace(/"/g, '&quot;');
            
            // Check if dashboard is currently open
            const isDashboardOpen = openDashboards.includes(src.id);
            const dashboardBtnClass = isDashboardOpen ? 'icon-btn-active' : 'icon-btn-primary';
            const dashboardBtnTooltip = isDashboardOpen ? 'ダッシュボードを閉じる' : 'ダッシュボードを表示';
            
            tr.innerHTML = `
                <td style="font-family: var(--font-outfit); font-weight: 600; font-size: 15px;">${escapeHtml(src.name)}</td>
                <td><span class="badge badge-type">${typeLabel}</span></td>
                <td style="font-family: var(--font-outfit); font-size: 14px;">${src.interval}</td>
                <td><span class="badge badge-datatype">${dataTypeLabel}</span></td>
                <td><span class="badge ${activeBadgeClass}">${activeText}</span></td>
                <td style="text-align: right;">
                    <div class="action-btns" style="justify-content: flex-end;">
                        <button class="icon-btn ${dashboardBtnClass}" title="${dashboardBtnTooltip}" onclick="openDashboard(${src.id})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line></svg>
                        </button>
                        <button class="icon-btn" title="アクティブ切り替え" onclick="toggleActive(${src.id})">
                            ${src.active ? 
                                `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>` : 
                                `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`
                            }
                        </button>
                        <button class="icon-btn" title="編集" onclick="openEditModal(${src.id}, '${escapeQuote(src.name)}', '${src.type}', '${safeConfig}', ${src.interval}, '${src.data_type}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                        </button>
                        <button class="icon-btn icon-btn-danger" title="データ履歴をクリア" onclick="clearSourceData(${src.id})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5V19A9 3 0 0 0 21 19V5"></path><path d="M3 12A9 3 0 0 0 21 12"></path><line x1="3" y1="21" x2="21" y2="3"></line></svg>
                        </button>
                        <button class="icon-btn icon-btn-danger" title="削除" onclick="deleteSource(${src.id})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load sources:", err);
    }
}

async function toggleActive(id) {
    try {
        await window.pywebview.api.toggle_source_active(id);
        loadSources();
    } catch (err) {
        console.error("Failed to toggle source active status:", err);
        alert("ステータス変更中にエラーが発生しました。\n" + err);
    }
}

async function deleteSource(id) {
    if (confirm("このデータソースを削除してもよろしいですか？データ履歴もすべて削除されます。")) {
        try {
            await window.pywebview.api.delete_source(id);
            loadSources();
        } catch (err) {
            console.error("Failed to delete source:", err);
            alert("削除中にエラーが発生しました。\n" + err);
        }
    }
}

async function clearSourceData(id) {
    if (confirm("このデータソースのデータ履歴のみを削除してもよろしいですか？データソースの設定は残ります。")) {
        try {
            await window.pywebview.api.clear_source_data(id);
            alert("データ履歴をクリアしました。");
            loadSources();
        } catch (err) {
            console.error("Failed to clear source data:", err);
            alert("データクリア中にエラーが発生しました。\n" + err);
        }
    }
}

function openDashboard(id) {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.toggle_dashboard(id);
    }
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function escapeQuote(str) {
    return str.replace(/'/g, "\\'");
}

function autoArrange() {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.auto_arrange_dashboards();
    }
}

// Initial Loading
window.addEventListener('pywebviewready', () => {
    loadSources();
    setInterval(loadSources, 3000);
});
