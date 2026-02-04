.PHONY: help build up down logs ps clean test-accounts init-strategy

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Show logs (follow)
	docker compose logs -f

ps: ## Show service status
	docker compose ps

clean: ## Stop and remove all containers, volumes, and data
	docker compose down -v
	rm -rf data/

restart: ## Restart all services
	docker compose restart

# Development helpers

test-accounts: ## Add test accounts
	@bash scripts/add-test-accounts.sh

init-strategy: ## Initialize delta neutral strategy
	@docker compose exec -T postgres psql -U trading -d trading_system < scripts/init-delta-neutral.sql
	@echo "✅ Delta neutral strategy initialized"

# Service-specific commands

predict-logs: ## Show predict-account logs
	docker compose logs -f predict-account

strategy-logs: ## Show strategy-engine logs
	docker compose logs -f strategy-engine

web-logs: ## Show web-api logs
	docker compose logs -f web-api

# Database commands

db-shell: ## Connect to PostgreSQL shell
	docker compose exec postgres psql -U trading -d trading_system

clickhouse-shell: ## Connect to ClickHouse shell
	docker compose exec clickhouse clickhouse-client

redis-cli: ## Connect to Redis CLI
	docker compose exec redis redis-cli

# Quick start

quickstart: build up test-accounts init-strategy ## Build, start, and initialize everything
	@echo ""
	@echo "✅ System ready!"
	@echo ""
	@echo "Services:"
	@echo "  - Predict Account API: http://localhost:8010"
	@echo "  - Strategy Engine:      http://localhost:8020"
	@echo "  - Web API:              http://localhost:8001"
	@echo "  - Web UI:               http://localhost:3000"
	@echo ""
	@echo "Next steps:"
	@echo "  make logs           - Watch logs"
	@echo "  make ps             - Check status"
	@echo "  make db-shell       - Connect to database"
