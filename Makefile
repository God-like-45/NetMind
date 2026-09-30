# NetMind Development Makefile
# Usage: make <target>
# Run 'make help' to see all available commands.

.PHONY: help setup dev-up dev-down dev-restart dev-logs \
        backend-install backend-test backend-lint backend-typecheck \
        frontend-install frontend-dev frontend-build \
        db-migrate db-rollback db-shell \
        clean docker-clean

# ─── Default target ──────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

# ─── Colors ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

help: ## Show this help message
	@echo ""
	@echo "NetMind Development Commands"
	@echo "─────────────────────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-25s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Environment Setup ───────────────────────────────────────────────────────
setup: ## Initial project setup - copy .env.example and install pre-commit
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)Created .env from .env.example. Edit it before running services.$(RESET)"; \
	else \
		echo ".env already exists."; \
	fi
	@cd backend && pip install -e ".[dev]"
	@pre-commit install
	@echo "$(GREEN)Setup complete.$(RESET)"

# ─── Docker Compose ──────────────────────────────────────────────────────────
dev-up: ## Start all Phase 1 services (postgres, redis, kafka, backend)
	docker compose up -d
	@echo "$(GREEN)Services starting. Run 'make dev-logs' to follow logs.$(RESET)"

dev-down: ## Stop and remove all containers (preserves volumes)
	docker compose down

dev-restart: ## Restart all services
	docker compose restart

dev-logs: ## Stream logs from all services
	docker compose logs -f

dev-logs-backend: ## Stream backend logs only
	docker compose logs -f backend

dev-status: ## Show service health status
	docker compose ps

dev-rebuild: ## Rebuild backend image and restart
	docker compose up -d --build backend

# ─── Backend ─────────────────────────────────────────────────────────────────
backend-install: ## Install backend Python dependencies
	cd backend && pip install -e ".[dev]"

backend-test: ## Run backend unit tests with coverage
	cd backend && pytest tests/unit/ -v --cov=netmind --cov-report=term-missing

backend-test-all: ## Run all backend tests (requires running infrastructure)
	cd backend && pytest -v

backend-lint: ## Run ruff linter on backend
	cd backend && ruff check netmind/ tests/
	cd backend && ruff format --check netmind/ tests/

backend-format: ## Auto-format backend code with ruff
	cd backend && ruff format netmind/ tests/
	cd backend && ruff check --fix netmind/ tests/

backend-typecheck: ## Run mypy type checking on backend
	cd backend && mypy netmind/

backend-dev: ## Run backend locally (requires .env with local settings)
	cd backend && uvicorn netmind.main:app --reload --host 0.0.0.0 --port 8000

# ─── Database ────────────────────────────────────────────────────────────────
db-migrate: ## Run pending Alembic migrations
	cd backend && alembic upgrade head

db-rollback: ## Roll back the last Alembic migration
	cd backend && alembic downgrade -1

db-revision: ## Create a new migration (usage: make db-revision MSG="add table")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-shell: ## Open a psql shell to the dev database
	docker compose exec postgres psql -U $${POSTGRES_USER:-netmind} -d $${POSTGRES_DB:-netmind}

db-history: ## Show Alembic migration history
	cd backend && alembic history --verbose

# ─── Frontend ────────────────────────────────────────────────────────────────
frontend-install: ## Install frontend Node dependencies
	cd frontend && npm install

frontend-dev: ## Run Next.js dev server
	cd frontend && npm run dev

frontend-build: ## Build Next.js production bundle
	cd frontend && npm run build

frontend-lint: ## Run ESLint on frontend
	cd frontend && npm run lint

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Remove Python cache files and test artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
	rm -rf backend/htmlcov backend/coverage.xml
	@echo "$(GREEN)Python cache cleaned.$(RESET)"

docker-clean: ## Remove NetMind containers and volumes (DESTROYS DATA)
	@echo "$(YELLOW)This will destroy all local data. Press Ctrl+C to cancel...$(RESET)"
	@sleep 3
	docker compose down -v
	docker image rm netmind-backend:latest 2>/dev/null || true
	@echo "$(GREEN)Docker resources cleaned.$(RESET)"

# ─── Secrets ─────────────────────────────────────────────────────────────────
generate-secret: ## Generate a random 32-byte hex secret for JWT_SECRET_KEY
	@python3 -c "import secrets; print(secrets.token_hex(32))"
