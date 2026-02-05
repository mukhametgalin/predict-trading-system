.PHONY: help build up down logs clean quickstart add-accounts init-strategy test-trade

# Default target
help:
	@echo "Predict Trading System"
	@echo ""
	@echo "Usage:"
	@echo "  make build          Build all Docker images"
	@echo "  make up             Start all services"
	@echo "  make down           Stop all services"
	@echo "  make logs           Show logs (all services)"
	@echo "  make logs-api       Show Web API logs"
	@echo "  make logs-predict   Show Predict Account logs"
	@echo "  make logs-strategy  Show Strategy Engine logs"
	@echo "  make logs-telegram  Show Telegram Bot logs"
	@echo "  make clean          Remove all containers and volumes"
	@echo "  make quickstart     Full setup: build, start, add accounts, init strategy"
	@echo "  make add-accounts   Add test accounts"
	@echo "  make init-strategy  Initialize Delta Neutral strategy"
	@echo "  make test-trade     Execute test trade (dry-run)"
	@echo "  make shell-api      Shell into Web API container"
	@echo "  make shell-db       PostgreSQL shell"
	@echo "  make shell-ch       ClickHouse shell"

# Build all images
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Show all logs
logs:
	docker compose logs -f

# Individual service logs
logs-api:
	docker compose logs -f web-api

logs-predict:
	docker compose logs -f predict-account

logs-strategy:
	docker compose logs -f strategy-engine

logs-telegram:
	docker compose logs -f telegram-bot

logs-ui:
	docker compose logs -f web-ui

# Clean up everything
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Full quickstart
quickstart: build up
	@echo "Waiting for services to start..."
	@sleep 10
	@make add-accounts
	@make init-strategy
	@echo ""
	@echo "✅ System is ready!"
	@echo ""
	@echo "Services:"
	@echo "  - Web UI:         http://localhost:3000"
	@echo "  - Web API:        http://localhost:8001"
	@echo "  - Predict API:    http://localhost:8010"
	@echo "  - Strategy:       http://localhost:8020"
	@echo ""
	@echo "Run 'make logs' to see all logs"

# Add test accounts
add-accounts:
	@echo "Adding test accounts..."
	@bash scripts/add-test-accounts.sh

# Initialize Delta Neutral strategy
init-strategy:
	@echo "Initializing Delta Neutral strategy..."
	@docker compose exec -T postgres psql -U trading -d trading_system < scripts/init-delta-neutral.sql

# Test trade (dry-run)
test-trade:
	@echo "Executing test trade (dry-run)..."
	@curl -s -X POST http://localhost:8010/trade \
		-H "Content-Type: application/json" \
		-d '{"account_id":"$(ACCOUNT_ID)","market_id":"$(MARKET_ID)","side":"yes","price":0.5,"shares":1,"confirm":false}' | jq .

# Shell access
shell-api:
	docker compose exec web-api /bin/bash

shell-db:
	docker compose exec postgres psql -U trading -d trading_system

shell-ch:
	docker compose exec clickhouse clickhouse-client -d markets

# Development helpers
dev-api:
	cd services/web-api && uvicorn main:app --reload --port 8001

dev-ui:
	cd ui/web && npm run dev

# Status check
status:
	@echo "=== Service Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Health Checks ==="
	@curl -s http://localhost:8001/health 2>/dev/null && echo " - Web API: OK" || echo " - Web API: DOWN"
	@curl -s http://localhost:8010/health 2>/dev/null && echo " - Predict: OK" || echo " - Predict: DOWN"
	@curl -s http://localhost:8011/health 2>/dev/null && echo " - Polymarket: OK" || echo " - Polymarket: DOWN"
	@curl -s http://localhost:8020/health 2>/dev/null && echo " - Strategy: OK" || echo " - Strategy: DOWN"
