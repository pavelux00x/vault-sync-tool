from flask import Blueprint, jsonify, request
from core.vault_client import VaultManager

api_bp = Blueprint('api', __name__)
vault_manager = VaultManager()

# ============ Cluster Management ============

@api_bp.route('/clusters', methods=['GET'])
def list_clusters():
    """List all configured clusters"""
    return jsonify(vault_manager.list_clusters())

@api_bp.route('/clusters', methods=['POST'])
def add_cluster():
    """Add a new cluster"""
    data = request.json
    if not data or not all(k in data for k in ['name', 'url', 'token']):
        return jsonify({'success': False, 'message': 'Missing required fields: name, url, token'}), 400
    
    result = vault_manager.add_cluster(
        name=data['name'],
        url=data['url'],
        token=data['token'],
        description=data.get('description', '')
    )
    return jsonify(result)

@api_bp.route('/clusters/<name>', methods=['PUT'])
def update_cluster(name):
    """Update an existing cluster"""
    data = request.json
    result = vault_manager.update_cluster(name, data)
    return jsonify(result)

@api_bp.route('/clusters/<name>', methods=['DELETE'])
def delete_cluster(name):
    """Delete a cluster"""
    result = vault_manager.delete_cluster(name)
    return jsonify(result)

@api_bp.route('/clusters/<name>/test', methods=['POST'])
def test_connection(name):
    """Test connection to a cluster"""
    result = vault_manager.test_connection(name)
    return jsonify(result)

@api_bp.route('/clusters/<name>/status', methods=['GET'])
def cluster_status(name):
    """Get detailed cluster status"""
    result = vault_manager.get_cluster_status(name)
    return jsonify(result)

# ============ Secrets Management ============

@api_bp.route('/clusters/<name>/secrets', methods=['GET'])
def list_secrets(name):
    """List all secrets in a cluster"""
    mount_point = request.args.get('mount_point', None)
    path = request.args.get('path', '')
    result = vault_manager.list_secrets(name, mount_point, path)
    return jsonify(result)

@api_bp.route('/clusters/<name>/secrets/tree', methods=['GET'])
def secrets_tree(name):
    """Get secrets as a tree structure"""
    result = vault_manager.get_secrets_tree(name)
    return jsonify(result)

@api_bp.route('/clusters/<name>/secret', methods=['GET'])
def read_secret(name):
    """Read a specific secret"""
    mount_point = request.args.get('mount_point')
    path = request.args.get('path')
    if not mount_point or not path:
        return jsonify({'success': False, 'message': 'mount_point and path are required'}), 400
    result = vault_manager.read_secret(name, mount_point, path)
    return jsonify(result)

@api_bp.route('/clusters/<name>/secret', methods=['POST'])
def create_secret(name):
    """Create or update a secret"""
    data = request.json
    if not data or not all(k in data for k in ['mount_point', 'path', 'data']):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    result = vault_manager.write_secret(name, data['mount_point'], data['path'], data['data'])
    return jsonify(result)

@api_bp.route('/clusters/<name>/secret', methods=['DELETE'])
def delete_secret(name):
    """Delete a secret"""
    mount_point = request.args.get('mount_point')
    path = request.args.get('path')
    if not mount_point or not path:
        return jsonify({'success': False, 'message': 'mount_point and path are required'}), 400
    result = vault_manager.delete_secret(name, mount_point, path)
    return jsonify(result)

# ============ Mount Points ============

@api_bp.route('/clusters/<name>/mounts', methods=['GET'])
def list_mounts(name):
    """List all mount points in a cluster"""
    result = vault_manager.list_mount_points(name)
    return jsonify(result)

# ============ Sync Operations ============

@api_bp.route('/sync', methods=['POST'])
def sync_secrets():
    """Sync secrets between clusters"""
    data = request.json
    if not data or not all(k in data for k in ['source_cluster', 'target_cluster', 'source_path', 'target_path']):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    result = vault_manager.sync_secrets(
        source_cluster=data['source_cluster'],
        target_cluster=data['target_cluster'],
        source_path=data['source_path'],
        target_path=data['target_path'],
        recursive=data.get('recursive', True)
    )
    return jsonify(result)

@api_bp.route('/sync/preview', methods=['POST'])
def preview_sync():
    """Preview what would be synced"""
    data = request.json
    if not data or not all(k in data for k in ['source_cluster', 'source_path']):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    result = vault_manager.preview_sync(
        source_cluster=data['source_cluster'],
        source_path=data['source_path']
    )
    return jsonify(result)

# ============ Export/Import ============

@api_bp.route('/clusters/<name>/export', methods=['POST'])
def export_secrets(name):
    """Export secrets to JSON"""
    data = request.json or {}
    mount_point = data.get('mount_point')
    path = data.get('path', '')
    result = vault_manager.export_secrets(name, mount_point, path)
    return jsonify(result)

@api_bp.route('/clusters/<name>/import', methods=['POST'])
def import_secrets(name):
    """Import secrets from JSON"""
    data = request.json
    if not data or 'secrets' not in data:
        return jsonify({'success': False, 'message': 'Missing secrets data'}), 400
    result = vault_manager.import_secrets(name, data['secrets'], data.get('mount_point'))
    return jsonify(result)

# ============ Configuration ============

@api_bp.route('/config/save', methods=['POST'])
def save_config():
    """Save current configuration to file"""
    result = vault_manager.save_config()
    return jsonify(result)

@api_bp.route('/config/load', methods=['POST'])
def load_config():
    """Load configuration from file"""
    result = vault_manager.load_config()
    return jsonify(result)