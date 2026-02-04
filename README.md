# common/tool

  * folder used for store scripts used for vault

# Backup / Import / Sync / List secrets

### Utils

```bash
make help

``` 


### File used for define clusters and actions 
```bash
cat inventory.yaml

``` 

### Actions inside inventory.yaml
```yaml
example1_import_sync: #Task name
  - conf:  "/oc/vault/resources/secrets/master.yaml" #File to source
    type: import #Operation to do with the file
  - conf:  "/oc/vault/resources/secrets/master-test.yaml"
    type: sync
example2_sync_import:
  - conf:  "/oc/vault/resources/secrets/ocp4.yaml"
    type: import
  - conf: "/oc/vault/resources/sync/ocp4.yaml"
    type: sync
```

### Import secrets 
```yaml
kind: "import" #import or sync
target: "master/ocp4/" #Destination cluster + path

secrets:
  paths:
    - /oc/etc/ns/jenkins-cicd/secret/* # Local path where to find secrets
```

### Sync secrets
```yaml
kind: "sync" #sync or import
source: "ocp4" #source vault cluster
target: "master" #destination vault cluster

jobs:
  - source_path: "ocp4/test-vault/" #secret stored in source
    destination_path: "ocp4/test-vault/" #where the secret will be stored in target cluster

  - source_path:
      - ocp4/test-backup/test-backup-sync
      - ocp4/test-backup/test-backup-sync3
      - ocp4/test-backup/test-backup-sync3
    destination_path: "ocp4/test-backup/"
```
