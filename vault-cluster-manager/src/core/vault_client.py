import os
import json
import yaml
import hvac
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'clusters.yaml')


class VaultCluster:
    """Represents a single Vault cluster connection"""
    
    def __init__(self, name: str, url: str, token: str, description: str = ''):
        self.name = name
        self.url = url
        self.token = token
        self.description = description
        self.client: Optional[hvac.Client] = None
        self.connected = False
        self.last_check: Optional[datetime] = None
        self.error: Optional[str] = None
    
    def connect(self) -> bool:
        """Establish connection to Vault"""
        try:
            self.client = hvac.Client(url=self.url, token=self.token, verify=False)
            if self.client.is_authenticated():
                self.connected = True
                self.error = None
                self.last_check = datetime.now()
                return True
            else:
                self.connected = False
                self.error = "Authentication failed"
                return False
        except Exception as e:
            self.connected = False
            self.error = str(e)
            return False
    
    def disconnect(self):
        """Disconnect from Vault"""
        self.client = None
        self.connected = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'url': self.url,
            'token': self.token,
            'description': self.description,
            'connected': self.connected,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'error': self.error
        }
    
    def to_safe_dict(self) -> Dict:
        """Convert to dictionary without sensitive data"""
        return {
            'name': self.name,
            'url': self.url,
            'description': self.description,
            'connected': self.connected,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'error': self.error
        }


class VaultManager:
    """Manages multiple Vault cluster connections"""
    
    def __init__(self):
        self.clusters: Dict[str, VaultCluster] = {}
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    # ============ Cluster Management ============
    
    def add_cluster(self, name: str, url: str, token: str, description: str = '') -> Dict:
        """Add a new cluster and test connection"""
        if name in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" already exists'}
        
        # Normalize URL
        url = url.rstrip('/')
        
        cluster = VaultCluster(name, url, token, description)
        if cluster.connect():
            self.clusters[name] = cluster
            return {
                'success': True,
                'message': f'Cluster "{name}" added and connected successfully',
                'cluster': cluster.to_safe_dict()
            }
        else:
            return {
                'success': False,
                'message': f'Failed to connect: {cluster.error}'
            }
    
    def update_cluster(self, name: str, data: Dict) -> Dict:
        """Update cluster configuration"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        
        if 'url' in data:
            cluster.url = data['url'].rstrip('/')
        if 'token' in data:
            cluster.token = data['token']
        if 'description' in data:
            cluster.description = data['description']
        
        # Reconnect with new settings
        cluster.disconnect()
        if cluster.connect():
            return {
                'success': True,
                'message': f'Cluster "{name}" updated successfully',
                'cluster': cluster.to_safe_dict()
            }
        else:
            return {
                'success': False,
                'message': f'Updated but failed to reconnect: {cluster.error}'
            }
    
    def delete_cluster(self, name: str) -> Dict:
        """Remove a cluster"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        self.clusters[name].disconnect()
        del self.clusters[name]
        return {'success': True, 'message': f'Cluster "{name}" removed'}
    
    def list_clusters(self) -> Dict:
        """List all clusters"""
        return {
            'success': True,
            'clusters': [c.to_safe_dict() for c in self.clusters.values()]
        }
    
    def test_connection(self, name: str) -> Dict:
        """Test connection to a cluster"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if cluster.connect():
            return {
                'success': True,
                'message': 'Connection successful',
                'cluster': cluster.to_safe_dict()
            }
        else:
            return {
                'success': False,
                'message': f'Connection failed: {cluster.error}'
            }
    
    def get_cluster_status(self, name: str) -> Dict:
        """Get detailed cluster status"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected or not cluster.client:
            cluster.connect()
        
        if not cluster.connected:
            return {
                'success': False,
                'message': f'Not connected: {cluster.error}'
            }
        
        try:
            # Get Vault status
            status = cluster.client.sys.read_health_status(method='GET')
            return {
                'success': True,
                'cluster': cluster.to_safe_dict(),
                'vault_status': {
                    'initialized': status.get('initialized', False),
                    'sealed': status.get('sealed', False),
                    'version': status.get('version', 'unknown'),
                    'cluster_name': status.get('cluster_name', 'unknown')
                }
            }
        except Exception as e:
            return {
                'success': True,
                'cluster': cluster.to_safe_dict(),
                'vault_status': {'error': str(e)}
            }
    
    # ============ Mount Points ============
    
    def list_mount_points(self, name: str) -> Dict:
        """List all secret mount points"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            response = cluster.client.sys.list_mounted_secrets_engines()
            mounts = []
            for path, config in response.get('data', response).items():
                mounts.append({
                    'path': path,
                    'type': config.get('type', 'unknown'),
                    'description': config.get('description', ''),
                    'options': config.get('options', {})
                })
            return {'success': True, 'mounts': sorted(mounts, key=lambda x: x['path'])}
        except hvac.exceptions.Forbidden:
            return {'success': False, 'message': 'Permission denied to list mount points'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    # ============ Secrets Operations ============
    
    def _list_recursive(self, client: hvac.Client, mount_point: str, path: str = '') -> List[str]:
        """Recursively list all secrets"""
        secrets = []
        try:
            response = client.secrets.kv.v2.list_secrets(path=path, mount_point=mount_point)
            keys = response.get('data', {}).get('keys', [])
            
            for key in keys:
                full_path = f"{path}{key}" if path else key
                if key.endswith('/'):
                    secrets.extend(self._list_recursive(client, mount_point, full_path))
                else:
                    secrets.append(f"{mount_point}/{full_path}")
        except hvac.exceptions.InvalidPath:
            pass
        except Exception:
            pass
        return secrets
    
    def list_secrets(self, name: str, mount_point: Optional[str] = None, path: str = '') -> Dict:
        """List secrets in a cluster"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            secrets = []
            
            if mount_point:
                # List secrets in specific mount point
                secrets = self._list_recursive(cluster.client, mount_point.rstrip('/'), path)
            else:
                # List secrets in all mount points
                mounts_result = self.list_mount_points(name)
                if mounts_result['success']:
                    for mount in mounts_result['mounts']:
                        if mount['type'] == 'kv':
                            mp = mount['path'].rstrip('/')
                            secrets.extend(self._list_recursive(cluster.client, mp, path))
            
            return {'success': True, 'secrets': secrets, 'count': len(secrets)}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_secrets_tree(self, name: str) -> Dict:
        """Get secrets organized as a tree structure"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            tree = {}
            mounts_result = self.list_mount_points(name)
            
            if mounts_result['success']:
                for mount in mounts_result['mounts']:
                    if mount['type'] == 'kv':
                        mp = mount['path'].rstrip('/')
                        secrets = self._list_recursive(cluster.client, mp)
                        tree[mp] = self._build_tree(secrets, mp)
            
            return {'success': True, 'tree': tree}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _build_tree(self, secrets: List[str], mount_point: str) -> Dict:
        """Build a tree structure from flat secret paths"""
        tree = {}
        prefix = f"{mount_point}/"
        
        for secret in secrets:
            if secret.startswith(prefix):
                path = secret[len(prefix):]
                parts = path.split('/')
                current = tree
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        current[part] = {'_is_secret': True, '_path': secret}
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
        return tree
    
    def read_secret(self, name: str, mount_point: str, path: str) -> Dict:
        """Read a specific secret"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            response = cluster.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point,
                raise_on_deleted_version=True
            )
            return {
                'success': True,
                'path': f"{mount_point}/{path}",
                'data': response['data']['data'],
                'metadata': response['data'].get('metadata', {})
            }
        except hvac.exceptions.InvalidPath:
            return {'success': False, 'message': 'Secret not found'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def write_secret(self, name: str, mount_point: str, path: str, data: Dict) -> Dict:
        """Write/update a secret"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            cluster.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                mount_point=mount_point,
                secret=data
            )
            return {
                'success': True,
                'message': f'Secret written to {mount_point}/{path}'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def delete_secret(self, name: str, mount_point: str, path: str) -> Dict:
        """Delete a secret"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        cluster = self.clusters[name]
        if not cluster.connected:
            cluster.connect()
        
        if not cluster.connected or not cluster.client:
            return {'success': False, 'message': f'Not connected: {cluster.error}'}
        
        try:
            cluster.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=mount_point
            )
            return {
                'success': True,
                'message': f'Secret {mount_point}/{path} deleted'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    # ============ Sync Operations ============
    
    def sync_secrets(self, source_cluster: str, target_cluster: str,
                     source_path: str, target_path: str, recursive: bool = True) -> Dict:
        """Sync secrets between clusters"""
        if source_cluster not in self.clusters:
            return {'success': False, 'message': f'Source cluster "{source_cluster}" not found'}
        if target_cluster not in self.clusters:
            return {'success': False, 'message': f'Target cluster "{target_cluster}" not found'}
        
        src = self.clusters[source_cluster]
        dst = self.clusters[target_cluster]
        
        if not src.connected:
            src.connect()
        if not dst.connected:
            dst.connect()
        
        if not src.connected:
            return {'success': False, 'message': f'Cannot connect to source: {src.error}'}
        if not dst.connected:
            return {'success': False, 'message': f'Cannot connect to target: {dst.error}'}
        
        try:
            src_mount, src_path_clean = self._parse_path(source_path)
            dst_mount, dst_path_clean = self._parse_path(target_path)
            
            synced = []
            errors = []
            
            if recursive and source_path.endswith('/'):
                self._sync_recursive(
                    src.client, dst.client,
                    src_mount, src_path_clean,
                    dst_mount, dst_path_clean,
                    synced, errors
                )
            else:
                result = self._sync_single(
                    src.client, dst.client,
                    src_mount, src_path_clean,
                    dst_mount, dst_path_clean
                )
                if result['success']:
                    synced.append(result['path'])
                else:
                    errors.append(result)
            
            return {
                'success': len(errors) == 0,
                'synced': synced,
                'errors': errors,
                'message': f'Synced {len(synced)} secrets, {len(errors)} errors'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _parse_path(self, full_path: str) -> tuple:
        """Parse mount point and path from full path"""
        clean = full_path.lstrip('/')
        parts = clean.split('/', 1)
        if len(parts) < 2:
            return parts[0], ''
        return parts[0], parts[1]
    
    def _sync_recursive(self, src_client, dst_client, src_mount, src_path,
                        dst_mount, dst_path, synced, errors):
        """Recursively sync secrets"""
        try:
            response = src_client.secrets.kv.v2.list_secrets(
                mount_point=src_mount, path=src_path
            )
            keys = response.get('data', {}).get('keys', [])
            
            for key in keys:
                curr_src = f"{src_path}{key}" if src_path else key
                curr_dst = f"{dst_path}{key}" if dst_path else key
                
                if key.endswith('/'):
                    self._sync_recursive(
                        src_client, dst_client,
                        src_mount, curr_src,
                        dst_mount, curr_dst,
                        synced, errors
                    )
                else:
                    result = self._sync_single(
                        src_client, dst_client,
                        src_mount, curr_src,
                        dst_mount, curr_dst
                    )
                    if result['success']:
                        synced.append(result['path'])
                    else:
                        errors.append(result)
        except hvac.exceptions.InvalidPath:
            errors.append({'path': f'{src_mount}/{src_path}', 'error': 'Path not found'})
    
    def _sync_single(self, src_client, dst_client, src_mount, src_path,
                     dst_mount, dst_path) -> Dict:
        """Sync a single secret"""
        try:
            response = src_client.secrets.kv.v2.read_secret_version(
                mount_point=src_mount, path=src_path, raise_on_deleted_version=True
            )
            data = response['data']['data']
            
            dst_client.secrets.kv.v2.create_or_update_secret(
                mount_point=dst_mount, path=dst_path, secret=data
            )
            return {'success': True, 'path': f'{dst_mount}/{dst_path}'}
        except hvac.exceptions.InvalidPath:
            return {'success': False, 'path': f'{src_mount}/{src_path}', 'error': 'Not found'}
        except Exception as e:
            return {'success': False, 'path': f'{src_mount}/{src_path}', 'error': str(e)}
    
    def preview_sync(self, source_cluster: str, source_path: str) -> Dict:
        """Preview what secrets would be synced"""
        if source_cluster not in self.clusters:
            return {'success': False, 'message': f'Cluster "{source_cluster}" not found'}
        
        src_mount, src_path_clean = self._parse_path(source_path)
        secrets = self._list_recursive(
            self.clusters[source_cluster].client, src_mount, src_path_clean
        )
        return {'success': True, 'secrets': secrets, 'count': len(secrets)}
    
    # ============ Export/Import ============
    
    def export_secrets(self, name: str, mount_point: Optional[str] = None,
                       path: str = '') -> Dict:
        """Export secrets as JSON"""
        secrets_list = self.list_secrets(name, mount_point, path)
        if not secrets_list['success']:
            return secrets_list
        
        cluster = self.clusters[name]
        exported = []
        
        for secret_path in secrets_list['secrets']:
            parts = secret_path.split('/', 1)
            if len(parts) >= 2:
                mp, p = parts[0], parts[1]
                result = self.read_secret(name, mp, p)
                if result['success']:
                    exported.append({
                        'path': secret_path,
                        'data': result['data']
                    })
        
        return {
            'success': True,
            'exported': exported,
            'count': len(exported)
        }
    
    def import_secrets(self, name: str, secrets: List[Dict],
                       mount_point: Optional[str] = None) -> Dict:
        """Import secrets from JSON"""
        if name not in self.clusters:
            return {'success': False, 'message': f'Cluster "{name}" not found'}
        
        imported = []
        errors = []
        
        for secret in secrets:
            path = secret.get('path', '')
            data = secret.get('data', {})
            
            if mount_point:
                mp = mount_point
                p = path
            else:
                parts = path.split('/', 1)
                if len(parts) >= 2:
                    mp, p = parts[0], parts[1]
                else:
                    errors.append({'path': path, 'error': 'Invalid path format'})
                    continue
            
            result = self.write_secret(name, mp, p, data)
            if result['success']:
                imported.append(path)
            else:
                errors.append({'path': path, 'error': result['message']})
        
        return {
            'success': len(errors) == 0,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {len(imported)} secrets, {len(errors)} errors'
        }
    
    # ============ Configuration ============
    
    def save_config(self) -> Dict:
        """Save configuration to file"""
        try:
            config = {
                'clusters': {
                    name: {
                        'url': c.url,
                        'token': c.token,
                        'description': c.description
                    }
                    for name, c in self.clusters.items()
                }
            }
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            return {'success': True, 'message': f'Configuration saved to {CONFIG_FILE}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            if not os.path.exists(CONFIG_FILE):
                return {'success': False, 'message': 'Configuration file not found'}
            
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
            
            loaded = []
            for name, data in config.get('clusters', {}).items():
                result = self.add_cluster(
                    name=name,
                    url=data['url'],
                    token=data['token'],
                    description=data.get('description', '')
                )
                if result['success']:
                    loaded.append(name)
            
            return {
                'success': True,
                'message': f'Loaded {len(loaded)} clusters',
                'clusters': loaded
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}