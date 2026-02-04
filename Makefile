USERF = $(shell cat .user)
ifeq ($(strip $(USERF)),)
USER = xx 
else
USER = $(strip $(USERF))
endif
ENV:= /$(USER)/vault/common/tool/.env
PYTHON_VERSION:= python3.12
INVENTORY:= /$(USER)/vault/common/tool/inventory.yaml
DEFAULT_DIR:= backup_vault/
VAULT_NODES := $(shell cat token.yaml | python3.12 -c 'import json, sys, yaml; y=yaml.safe_load(sys.stdin.read()); print(json.dumps(y))' | jq -cr '."vault_cfg".clusters | keys[]')

help:
	@echo
	@echo "=================================="
	@echo "          VAULT Commands         "
	@echo "=================================="
	@echo
	@echo "#Want to apply some configurations? Check the inventory.yaml file"
	@echo
	@echo "#Current clusters"
	@$(foreach node,$(VAULT_NODES), echo "NODE=$(node)";) 
	@echo
	@echo
	@echo "make \$${NODE}_import # Import secrets to CLUSTER"
	@echo "make \$${NODE}_sync # Sync secrets to CLUSTER"
	@echo "make \$${NODE}_backup  # Export Secrets to folder (Defined in Makefile)"
	@echo "make \$${NODE}_list # List CLUSTER secret" 

%_import:	
	@$(PYTHON_VERSION) vault_tool.py import --vault $(subst _import,,$@) $(OPT) || true  

%_sync:	
	@$(PYTHON_VERSION) vault_tool.py sync --vault $(subst _sync,,$@) $(OPT) 

%_backup:	
	@-mkdir -p $(DEFAULT_DIR)
	@$(PYTHON_VERSION) vault_tool.py backup --src $(subst _backup,,$@) --dir $(DEFAULT_DIR)

%_list:
	@$(PYTHON_VERSION) vault_tool.py list --src $(subst _list,,$@) $(if $(cluster), --cluster $(cluster)) $(if $(inline), --inline $(inline))

nodes:
	@echo $(VAULT_NODES)
