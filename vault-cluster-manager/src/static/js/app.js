// Global state
let currentCluster = null;
let currentSecret = null;
let secretsData = {};
let mountPoints = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadClusters();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Filter secrets
    document.getElementById('secretsFilter').addEventListener('input', (e) => {
        filterSecrets(e.target.value);
    });

    // Import file handler
    document.getElementById('importFile').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                document.getElementById('importData').value = event.target.result;
            };
            reader.readAsText(file);
        }
    });
}

// ============ API Helpers ============

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    try {
        const response = await fetch(`/api${endpoint}`, options);
        return await response.json();
    } catch (error) {
        showToast('Error', error.message, 'error');
        return { success: false, message: error.message };
    }
}

// ============ Toast Notifications ============

function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    toast.className = `toast ${type}`;
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// ============ Cluster Management ============

async function loadClusters() {
    const result = await apiCall('/clusters');
    if (result.success) {
        renderClustersList(result.clusters);
        updateSyncDropdowns(result.clusters);
    }
}

function renderClustersList(clusters) {
    const container = document.getElementById('clustersList');
    
    if (clusters.length === 0) {
        container.innerHTML = '<div class="p-3 text-muted text-center">No clusters configured</div>';
        return;
    }
    
    container.innerHTML = clusters.map(cluster => `
        <div class="list-group-item cluster-item ${currentCluster === cluster.name ? 'active' : ''}" 
             onclick="selectCluster('${cluster.name}')">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <span class="status-indicator ${cluster.connected ? 'connected' : 'disconnected'}"></span>
                    <strong>${cluster.name}</strong>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary" onclick="event.stopPropagation(); testCluster('${cluster.name}')" title="Test Connection">
                        <i class="bi bi-plug"></i>
                    </button>
                    <button class="btn btn-outline-secondary" onclick="event.stopPropagation(); showEditClusterModal('${cluster.name}')" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="event.stopPropagation(); deleteCluster('${cluster.name}')" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <small class="text-muted d-block mt-1">${cluster.url}</small>
            ${cluster.description ? `<small class="text-muted">${cluster.description}</small>` : ''}
        </div>
    `).join('');
}

async function addCluster() {
    const name = document.getElementById('clusterName').value.trim();
    const url = document.getElementById('clusterUrl').value.trim();
    const token = document.getElementById('clusterToken').value.trim();
    const description = document.getElementById('clusterDescription').value.trim();
    
    if (!name || !url || !token) {
        showToast('Error', 'Please fill in all required fields', 'error');
        return;
    }
    
    const result = await apiCall('/clusters', 'POST', { name, url, token, description });
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('addClusterModal')).hide();
        document.getElementById('clusterName').value = '';
        document.getElementById('clusterUrl').value = '';
        document.getElementById('clusterToken').value = '';
        document.getElementById('clusterDescription').value = '';
        loadClusters();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function testCluster(name) {
    showToast('Testing', `Testing connection to ${name}...`, 'info');
    const result = await apiCall(`/clusters/${name}/test`, 'POST');
    
    if (result.success) {
        showToast('Success', 'Connection successful', 'success');
        loadClusters();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteCluster(name) {
    if (!confirm(`Are you sure you want to delete cluster "${name}"?`)) {
        return;
    }
    
    const result = await apiCall(`/clusters/${name}`, 'DELETE');
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        if (currentCluster === name) {
            currentCluster = null;
            document.getElementById('clusterInfoBar').classList.add('d-none');
            document.getElementById('secretsTree').innerHTML = '';
        }
        loadClusters();
    } else {
        showToast('Error', result.message, 'error');
    }
}

function showEditClusterModal(name) {
    // For simplicity, we'll need to store cluster data or fetch it
    document.getElementById('editClusterOriginalName').value = name;
    const modal = new bootstrap.Modal(document.getElementById('editClusterModal'));
    modal.show();
}

async function updateCluster() {
    const name = document.getElementById('editClusterOriginalName').value;
    const url = document.getElementById('editClusterUrl').value.trim();
    const token = document.getElementById('editClusterToken').value.trim();
    const description = document.getElementById('editClusterDescription').value.trim();
    
    const data = {};
    if (url) data.url = url;
    if (token) data.token = token;
    if (description) data.description = description;
    
    const result = await apiCall(`/clusters/${name}`, 'PUT', data);
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('editClusterModal')).hide();
        loadClusters();
    } else {
        showToast('Error', result.message, 'error');
    }
}

function toggleTokenVisibility() {
    const input = document.getElementById('clusterToken');
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ============ Cluster Selection ============

async function selectCluster(name) {
    currentCluster = name;
    
    // Update UI
    document.querySelectorAll('.cluster-item').forEach(el => {
        el.classList.remove('active');
        if (el.querySelector('strong').textContent === name) {
            el.classList.add('active');
        }
    });
    
    // Show info bar
    const infoBar = document.getElementById('clusterInfoBar');
    infoBar.classList.remove('d-none');
    document.getElementById('currentClusterName').textContent = name;
    
    // Load cluster data
    await loadMountPoints();
    await loadSecretsTree();
    
    // Get cluster status
    const status = await apiCall(`/clusters/${name}/status`);
    if (status.success) {
        document.getElementById('currentClusterUrl').textContent = ` - ${status.cluster.url}`;
        const badge = document.getElementById('clusterStatus');
        if (status.cluster.connected) {
            badge.className = 'badge bg-success';
            badge.textContent = 'Connected';
        } else {
            badge.className = 'badge bg-danger';
            badge.textContent = 'Disconnected';
        }
    }
}

// ============ Mount Points ============

async function loadMountPoints() {
    if (!currentCluster) return;
    
    const result = await apiCall(`/clusters/${currentCluster}/mounts`);
    
    if (result.success) {
        mountPoints = result.mounts;
        renderMountsTable(result.mounts);
        updateMountDropdowns(result.mounts);
    }
}

function renderMountsTable(mounts) {
    const tbody = document.getElementById('mountsTable');
    tbody.innerHTML = mounts.map(mount => `
        <tr onclick="browseMountPoint('${mount.path}')">
            <td><i class="bi bi-folder text-warning"></i> ${mount.path}</td>
            <td><span class="badge bg-secondary">${mount.type}</span></td>
            <td>${mount.description || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); browseMountPoint('${mount.path}')">
                    <i class="bi bi-search"></i> Browse
                </button>
            </td>
        </tr>
    `).join('');
}

function updateMountDropdowns(mounts) {
    const kvMounts = mounts.filter(m => m.type === 'kv');
    const options = kvMounts.map(m => `<option value="${m.path.replace('/', '')}">${m.path}</option>`).join('');
    
    document.getElementById('newSecretMount').innerHTML = options;
    document.getElementById('exportMountPoint').innerHTML = '<option value="">All mount points</option>' + options;
}

async function browseMountPoint(path) {
    document.querySelector('a[href="#secretsTab"]').click();
    await loadSecretsTree(path.replace('/', ''));
}

// ============ Secrets Tree ============

async function loadSecretsTree(mountPoint = null) {
    if (!currentCluster) return;
    
    const container = document.getElementById('secretsTree');
    container.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm"></div> Loading...</div>';
    
    const result = await apiCall(`/clusters/${currentCluster}/secrets/tree`);
    
    if (result.success) {
        secretsData = result.tree;
        renderSecretsTree(result.tree);
    } else {
        container.innerHTML = `<div class="text-danger p-3">${result.message}</div>`;
    }
}

function renderSecretsTree(tree) {
    const container = document.getElementById('secretsTree');
    container.innerHTML = buildTreeHTML(tree, '');
}

function buildTreeHTML(node, path) {
    let html = '';
    
    for (const [key, value] of Object.entries(node)) {
        if (key === '_is_secret' || key === '_path') continue;
        
        const fullPath = path ? `${path}/${key}` : key;
        const isSecret = value._is_secret === true;
        
        if (isSecret) {
            html += `
                <div class="tree-node secret" onclick="loadSecret('${value._path}')" data-path="${value._path}">
                    <i class="bi bi-key node-icon"></i>
                    <span>${key}</span>
                </div>
            `;
        } else {
            const childrenHTML = buildTreeHTML(value, fullPath);
            html += `
                <div class="tree-folder">
                    <div class="tree-node folder" onclick="toggleFolder(this)">
                        <span class="tree-toggle"><i class="bi bi-chevron-right"></i></span>
                        <i class="bi bi-folder node-icon"></i>
                        <span>${key}</span>
                    </div>
                    <div class="tree-children" style="display: none;">
                        ${childrenHTML}
                    </div>
                </div>
            `;
        }
    }
    
    return html;
}

function toggleFolder(element) {
    const children = element.nextElementSibling;
    const toggle = element.querySelector('.tree-toggle i');
    
    if (children.style.display === 'none') {
        children.style.display = 'block';
        toggle.className = 'bi bi-chevron-down';
    } else {
        children.style.display = 'none';
        toggle.className = 'bi bi-chevron-right';
    }
}

function filterSecrets(query) {
    const nodes = document.querySelectorAll('.tree-node');
    query = query.toLowerCase();
    
    nodes.forEach(node => {
        const text = node.textContent.toLowerCase();
        const parent = node.closest('.tree-folder');
        
        if (query === '' || text.includes(query)) {
            node.style.display = 'flex';
            if (parent) {
                parent.style.display = 'block';
                const children = parent.querySelector('.tree-children');
                if (children && query !== '') {
                    children.style.display = 'block';
                    const toggle = parent.querySelector('.tree-toggle i');
                    if (toggle) toggle.className = 'bi bi-chevron-down';
                }
            }
        } else {
            if (node.classList.contains('secret')) {
                node.style.display = 'none';
            }
        }
    });
}

// ============ Secret Operations ============

async function loadSecret(path) {
    if (!currentCluster) return;
    
    // Update selection
    document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('selected'));
    const node = document.querySelector(`.tree-node[data-path="${path}"]`);
    if (node) node.classList.add('selected');
    
    const parts = path.split('/');
    const mountPoint = parts[0];
    const secretPath = parts.slice(1).join('/');
    
    const result = await apiCall(`/clusters/${currentCluster}/secret?mount_point=${mountPoint}&path=${secretPath}`);
    
    if (result.success) {
        currentSecret = { mountPoint, path: secretPath, fullPath: path, data: result.data };
        renderSecretContent(result);
        document.getElementById('secretActions').classList.remove('d-none');
    } else {
        document.getElementById('secretContent').innerHTML = `<div class="alert alert-danger">${result.message}</div>`;
        document.getElementById('secretActions').classList.add('d-none');
    }
}

function renderSecretContent(result) {
    document.getElementById('secretPath').textContent = result.path;
    
    const container = document.getElementById('secretContent');
    const data = result.data;
    
    let html = '';
    for (const [key, value] of Object.entries(data)) {
        const displayValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
        const maskedValue = '•'.repeat(Math.min(displayValue.length, 20));
        
        html += `
            <div class="secret-key-value">
                <div class="secret-key">${escapeHtml(key)}</div>
                <div class="secret-value masked" data-value="${escapeHtml(displayValue)}">${maskedValue}</div>
                <span class="toggle-visibility" onclick="toggleSecretValue(this)">
                    <i class="bi bi-eye"></i>
                </span>
            </div>
        `;
    }
    
    container.innerHTML = html || '<p class="text-muted">This secret has no data</p>';
}

function toggleSecretValue(element) {
    const valueEl = element.previousElementSibling;
    const icon = element.querySelector('i');
    
    if (valueEl.classList.contains('masked')) {
        valueEl.textContent = valueEl.dataset.value;
        valueEl.classList.remove('masked');
        icon.className = 'bi bi-eye-slash';
    } else {
        valueEl.textContent = '•'.repeat(Math.min(valueEl.dataset.value.length, 20));
        valueEl.classList.add('masked');
        icon.className = 'bi bi-eye';
    }
}

function editSecret() {
    if (!currentSecret) return;
    
    document.getElementById('editSecretPath').value = currentSecret.fullPath;
    document.getElementById('editSecretData').value = JSON.stringify(currentSecret.data, null, 2);
    
    const modal = new bootstrap.Modal(document.getElementById('editSecretModal'));
    modal.show();
}

async function saveSecret() {
    const path = document.getElementById('editSecretPath').value;
    let data;
    
    try {
        data = JSON.parse(document.getElementById('editSecretData').value);
    } catch (e) {
        showToast('Error', 'Invalid JSON format', 'error');
        return;
    }
    
    const parts = path.split('/');
    const mountPoint = parts[0];
    const secretPath = parts.slice(1).join('/');
    
    const result = await apiCall(`/clusters/${currentCluster}/secret`, 'POST', {
        mount_point: mountPoint,
        path: secretPath,
        data: data
    });
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('editSecretModal')).hide();
        loadSecret(path);
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteCurrentSecret() {
    if (!currentSecret) return;
    
    if (!confirm(`Are you sure you want to delete "${currentSecret.fullPath}"?`)) {
        return;
    }
    
    const result = await apiCall(
        `/clusters/${currentCluster}/secret?mount_point=${currentSecret.mountPoint}&path=${currentSecret.path}`,
        'DELETE'
    );
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        currentSecret = null;
        document.getElementById('secretContent').innerHTML = '<p class="text-muted">Select a secret to view its contents</p>';
        document.getElementById('secretPath').textContent = '';
        document.getElementById('secretActions').classList.add('d-none');
        loadSecretsTree();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function createSecret() {
    if (!currentCluster) {
        showToast('Error', 'Please select a cluster first', 'error');
        return;
    }
    
    const mountPoint = document.getElementById('newSecretMount').value;
    const path = document.getElementById('newSecretPath').value.trim();
    let data;
    
    try {
        data = JSON.parse(document.getElementById('newSecretData').value);
    } catch (e) {
        showToast('Error', 'Invalid JSON format', 'error');
        return;
    }
    
    if (!mountPoint || !path) {
        showToast('Error', 'Please fill in mount point and path', 'error');
        return;
    }
    
    const result = await apiCall(`/clusters/${currentCluster}/secret`, 'POST', {
        mount_point: mountPoint,
        path: path,
        data: data
    });
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        document.getElementById('newSecretPath').value = '';
        document.getElementById('newSecretData').value = '';
        loadSecretsTree();
    } else {
        showToast('Error', result.message, 'error');
    }
}

function refreshSecrets() {
    loadSecretsTree();
    loadMountPoints();
}

// ============ Sync Operations ============

function updateSyncDropdowns(clusters) {
    const options = clusters.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    document.getElementById('syncSourceCluster').innerHTML = options;
    document.getElementById('syncTargetCluster').innerHTML = options;
}

async function previewSync() {
    const sourceCluster = document.getElementById('syncSourceCluster').value;
    const sourcePath = document.getElementById('syncSourcePath').value;
    
    if (!sourceCluster || !sourcePath) {
        showToast('Error', 'Please fill in source cluster and path', 'error');
        return;
    }
    
    const result = await apiCall('/sync/preview', 'POST', {
        source_cluster: sourceCluster,
        source_path: sourcePath
    });
    
    if (result.success) {
        showToast('Preview', `Found ${result.count} secrets to sync`, 'info');
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function executeSync() {
    const sourceCluster = document.getElementById('syncSourceCluster').value;
    const targetCluster = document.getElementById('syncTargetCluster').value;
    const sourcePath = document.getElementById('syncSourcePath').value;
    const targetPath = document.getElementById('syncTargetPath').value;
    
    if (!sourceCluster || !targetCluster || !sourcePath || !targetPath) {
        showToast('Error', 'Please fill in all fields', 'error');
        return;
    }
    
    if (!confirm(`Sync from ${sourceCluster}:${sourcePath} to ${targetCluster}:${targetPath}?`)) {
        return;
    }
    
    const result = await apiCall('/sync', 'POST', {
        source_cluster: sourceCluster,
        target_cluster: targetCluster,
        source_path: sourcePath,
        target_path: targetPath,
        recursive: sourcePath.endsWith('/')
    });
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        if (currentCluster === targetCluster) {
            loadSecretsTree();
        }
    } else {
        showToast('Error', result.message, 'error');
    }
}

// ============ Export/Import ============

async function showExportModal() {
    if (!currentCluster) {
        showToast('Error', 'Please select a cluster first', 'error');
        return;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();
    
    const mountPoint = document.getElementById('exportMountPoint').value;
    const result = await apiCall(`/clusters/${currentCluster}/export`, 'POST', {
        mount_point: mountPoint || null
    });
    
    if (result.success) {
        document.getElementById('exportData').value = JSON.stringify(result.exported, null, 2);
    } else {
        document.getElementById('exportData').value = `Error: ${result.message}`;
    }
}

function copyExport() {
    const data = document.getElementById('exportData').value;
    navigator.clipboard.writeText(data).then(() => {
        showToast('Success', 'Copied to clipboard', 'success');
    });
}

function downloadExport() {
    const data = document.getElementById('exportData').value;
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vault-export-${currentCluster}-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function showImportModal() {
    if (!currentCluster) {
        showToast('Error', 'Please select a cluster first', 'error');
        return;
    }
    const modal = new bootstrap.Modal(document.getElementById('importModal'));
    modal.show();
}

async function executeImport() {
    let secrets;
    
    try {
        secrets = JSON.parse(document.getElementById('importData').value);
    } catch (e) {
        showToast('Error', 'Invalid JSON format', 'error');
        return;
    }
    
    const result = await apiCall(`/clusters/${currentCluster}/import`, 'POST', { secrets });
    
    if (result.success) {
        showToast('Success', result.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
        loadSecretsTree();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// ============ Configuration ============

async function saveConfig() {
    const result = await apiCall('/config/save', 'POST');
    showToast(result.success ? 'Success' : 'Error', result.message, result.success ? 'success' : 'error');
}

async function loadConfig() {
    const result = await apiCall('/config/load', 'POST');
    if (result.success) {
        showToast('Success', result.message, 'success');
        loadClusters();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// ============ Utilities ============

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}