# Vault Secrets Manager

A utility for managing secrets across Vault clusters with support for backup, import, sync, and list operations.


## Roadmap

### Coming Soon

- **SSL/TLS Verification**: 


## Quick Start

```bash
make help
```

## Configuration

### Inventory File

Define your clusters and actions in `inventory.yaml`:

```bash
cat inventory.yaml # You will see an example inventory file with cluster definitions and action sequences.
```

### Token File

Provide Vault tokens for each cluster in `token.yaml`:
> **Important:** The cluster names in `token.yaml` must match exactly with the cluster names defined in `inventory.yaml`.

```bash
cat token.yaml # 
```


### Task Definition

Tasks are defined as a list of operations to execute sequentially:

```yaml
actions:
  example1_import_sync:
    - conf: "/user/vault/resources/secrets/master.yaml"
      type: import
    - conf: "/user/vault/resources/secrets/master-test.yaml"
      type: sync

  example2_sync_import:
    - conf: "/user/vault/resources/secrets/ocp4.yaml"
      type: import
    - conf: "/user/vault/resources/sync/ocp4.yaml"
      type: sync
```

| Field | Description |
|-------|-------------|
| `actions.<custom_name>` | Custom identifier for the action sequence |
| `conf` | Path to the configuration file for the operation |
| `type` | Operation type (`import` or `sync`) |


## Usage

Execute operations defined in your inventory file using Make targets:

| Command | Description |
|---------|-------------|
| `make <clustername>_import` | Import secrets to the specified cluster based on inventory configuration |
| `make <clustername>_sync` | Sync secrets for the specified cluster based on inventory configuration |
| `make <clustername>_backup` | Backup secrets from the specified cluster |
| `make <clustername>_list` | List secrets in the specified cluster |

**Example:**
```bash
make example1_import_sync  # Executes import and sync operations
make example2_sync_import  # Executes sync and import operations
```

## Operations

### Import Secrets

Import secrets from local files to a Vault cluster.

```yaml
kind: "import"
target: "master/ocp4/"  # Destination cluster + path

secrets:
  paths:
    - /user/etc/ns/jenkins-cicd/secret/*  # Local path containing secrets
```

| Field | Description |
|-------|-------------|
| `kind` | Operation type (`import`) |
| `target` | Destination cluster and path |
| `secrets.paths` | List of local paths to import |

### Sync Secrets

Synchronize secrets between Vault clusters.

```yaml
kind: "sync"
source: "userp4"   # Source Vault cluster
target: "master" # Destination Vault cluster

jobs:
  - source_path: "ocp4/test-vault/"
    destination_path: "ocp4/test-vault/"

  - source_path:
      - ocp4/test-backup/test-backup-sync
      - ocp4/test-backup/test-backup-sync3
      - ocp4/test-backup/test-backup-sync3
    destination_path: "ocp4/test-backup/"
```

| Field | Description |
|-------|-------------|
| `kind` | Operation type (`sync`) |
| `source` | Source Vault cluster |
| `target` | Destination Vault cluster |
| `jobs[].source_path` | Path(s) in source cluster (string or list) |
| `jobs[].destination_path` | Path in destination cluster |



### Start docker

```bash
#Start
for i in {1,2}; do 
  $(which docker) run -dit -p 820$i:8200 --name vault-$i hashicorp/vault:latest;
done

#Fetch these tokens to use in inventory.yaml
for i in {1,2}; do 
  token=$($(which docker) logs vault-$i | grep "Root Token" | awk '{print $NF}')
  echo "Token vault $i: $token" 
done

#Stop
for i in {1,2}; do 
  $(which docker) rm -f vault-$i
done


```

---