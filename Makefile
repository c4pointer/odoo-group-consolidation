# Developer entry points. Every target runs inside Docker; only `make lint` needs ruff locally.
DB       ?= delta
TEST_DB  ?= delta_test
BARE_DB  ?= delta_clean
MODULE   := account_group_consolidation
DEMO     := account_group_consolidation_demo
COMPOSE  := docker compose
ODOO     := $(COMPOSE) run --rm -T odoo odoo
DROPDB   := $(COMPOSE) exec -T db dropdb -U odoo --if-exists --force

.DEFAULT_GOAL := help
.PHONY: help up down logs demo bare demo-data test harness lint fmt shell

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

up: ## Start PostgreSQL and Odoo (http://localhost:8020)
	$(COMPOSE) up -d

down: ## Stop all containers (data volumes are kept)
	$(COMPOSE) down

logs: ## Follow the Odoo log
	$(COMPOSE) logs -f odoo

demo: ## Recreate the demo database with the module and Delta Group demo data, then start Odoo
	$(COMPOSE) up -d --wait db
	$(COMPOSE) stop odoo
	$(DROPDB) $(DB)
	$(ODOO) -d $(DB) -i $(DEMO) --stop-after-init
	$(COMPOSE) up -d odoo
	@echo "Ready: http://localhost:$${ODOO_PORT:-8020}  (db: $(DB), login: admin / admin)"

bare: ## Recreate an empty database (delta_clean, base only) to install the module from Apps
	$(COMPOSE) up -d --wait db
	$(COMPOSE) stop odoo
	$(DROPDB) $(BARE_DB)
	$(ODOO) -d $(BARE_DB) -i base --stop-after-init
	$(COMPOSE) up -d odoo
	@echo "Ready: http://localhost:$${ODOO_PORT:-8020}/web?db=$(BARE_DB)  (login: admin / admin)"

demo-data: ## Load the demo data into an existing database: make demo-data DB=delta_clean
	$(COMPOSE) up -d --wait db
	$(COMPOSE) stop odoo
	$(ODOO) -d $(DB) -i $(DEMO) --stop-after-init
	$(COMPOSE) up -d odoo
	@echo "Demo data loaded: http://localhost:$${ODOO_PORT:-8020}/web?db=$(DB)  (login: admin / admin)"

test: ## Run the module's tests on a throw-away database
	$(COMPOSE) up -d --wait db
	$(DROPDB) $(TEST_DB)
	$(ODOO) -d $(TEST_DB) -i $(MODULE) --test-tags /$(MODULE) --stop-after-init --log-level=test

harness: ## Test the Claude Code hooks in .claude/hooks
	python3 -I -m unittest discover -s .claude/hooks

lint: ## Static checks (ruff)
	ruff check addons .claude/hooks
	ruff format --check addons .claude/hooks

fmt: ## Auto-format Python code
	ruff format addons .claude/hooks
	ruff check --fix addons .claude/hooks

shell: ## Odoo shell on the demo database
	$(COMPOSE) run --rm odoo odoo shell -d $(DB)
