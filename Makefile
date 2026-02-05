# Configuration
USERF := $(shell cat .user 2>/dev/null)
USER := $(if $(strip $(USERF)),$(strip $(USERF)),default_user)
PYTHON_VERSION := python3.12
PIP := pip3.12
GUI_FOLDER := /$(USER)/vault/export/tool/gui/vault-cluster-manager
INVENTORY := /$(USER)/vault/export/tool/inventory.yaml
DEFAULT_DIR := backup_vault/
VAULT_NODES := $(shell cat token.yaml 2>/dev/null | $(PYTHON_VERSION) -c 'import json, sys, yaml; y=yaml.safe_load(sys.stdin.read()); print(json.dumps(y))' | jq -cr '."vault_cfg".clusters | keys[]')

.PHONY: help nodes %_import %_sync %_backup %_list

help:
	@echo ""
	@echo "=================================="
	@echo "          VAULT Commands         "
	@echo "=================================="
	@echo ""
	@echo "Current clusters:"
	@$(foreach node,$(VAULT_NODES),echo "  - $(node)";)
	@echo ""
	@echo "Available commands:"
	@echo "  make <NODE>_import   # Import secrets to CLUSTER"
	@echo "  make <NODE>_sync     # Sync secrets to CLUSTER"
	@echo "  make <NODE>_backup   # Export secrets to $(DEFAULT_DIR)"
	@echo "  make <NODE>_list     # List CLUSTER secrets"
	@echo "  make nodes           # Show all cluster nodes"
	@echo ""
	@echo "Check $(INVENTORY) for configuration"

%_import:	
	@$(PYTHON_VERSION) vault_tool.py import --vault $(subst _import,,$@) $(OPT) || true

%_sync:	
	@$(PYTHON_VERSION) vault_tool.py sync --vault $(subst _sync,,$@) $(OPT)

%_backup:	
	@mkdir -p $(DEFAULT_DIR)
	@$(PYTHON_VERSION) vault_tool.py backup --src $(subst _backup,,$@) --dir $(DEFAULT_DIR)

%_list:
	@$(PYTHON_VERSION) vault_tool.py list --src $(subst _list,,$@) $(if $(cluster),--cluster $(cluster)) $(if $(inline),--inline $(inline))

nodes:
	@echo $(VAULT_NODES)

install-gui:
	@$(PIP) install -r $(GUI_FOLDER)/requirements.txt

start-gui:
	@$(PYTHON_VERSION) $(GUI_FOLDER)/src/main.py

