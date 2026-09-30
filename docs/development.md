# Development Guide

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Docker | 24.0 | Container runtime |
| Docker Compose | v2.20 | Local orchestration |
| Python | 3.11 | Backend development |
| Node.js | 20.0 | Frontend development |
| Git | 2.40 | Version control |

---

## First-Time Setup

```bash
# 1. Clone
git clone <repo-url>
cd netmind

# 2. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 3. Copy environment file
cp .env.example .env

# 4. Generate secrets
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
# Add output to .env

# 5. Set remaining required variables in .env:
#   POSTGRES_PASSWORD=<choose a strong password>
#   REDIS_PASSWORD=<choose a strong password>
#   JWT_SECRET_KEY=<generated above>

# 6. Start infrastructure
docker compose up -d

# 7. Wait for services to be healthy
docker compose ps

# 8. Run migrations
make db-migrate

# 9. Verify
curl http://localhost:8000/health
```

---

## Daily Development Workflow

```bash
# Start services if not running
make dev-up

# Backend development (with hot reload)
make backend-dev

# Frontend development
make frontend-dev     # Runs Next.js dev server on :3000

# Run tests before committing
make backend-test

# Check linting
make backend-lint

# Stop services
make dev-down
```

---

## Backend Development

### Project Structure

```
backend/netmind/
├── app.py            Application factory
├── main.py           ASGI entry point
├── api/
│   ├── dependencies.py     FastAPI dependency providers
│   ├── exception_handlers.py
│   └── v1/
│       ├── router.py
│       └── endpoints/
│           └── health.py
├── core/
│   ├── config.py     Settings (pydantic-settings)
│   ├── exceptions.py  Exception hierarchy
│   └── logging.py    Structured logging
├── db/
│   ├── session.py    Async engine + session factory
│   └── migrations/   Alembic migrations
├── models/           SQLAlchemy ORM models
├── schemas/          Pydantic request/response schemas
├── services/         Business logic
└── workers/          Kafka consumers (Phase 2+)
```

### Adding a New Endpoint

1. Create schema in `netmind/schemas/`
2. Create service in `netmind/services/`
3. Create endpoint in `netmind/api/v1/endpoints/`
4. Register router in `netmind/api/v1/router.py`
5. Write tests in `tests/unit/`

### Adding a Database Table

1. Define ORM model in `netmind/models/`
2. Import model in `netmind/db/migrations/env.py`
3. Create migration: `make db-revision MSG="add <table> table"`
4. Review generated migration in `netmind/db/migrations/versions/`
5. Apply: `make db-migrate`

### Running Tests

```bash
# Unit tests only (no infrastructure needed)
make backend-test

# Specific test file
cd backend && pytest tests/unit/test_config.py -v

# With coverage report
cd backend && pytest tests/unit/ --cov=netmind --cov-report=html

# Integration tests (require running Docker services)
cd backend && pytest tests/integration/ -v
```

### Linting and Formatting

```bash
# Check lint
make backend-lint

# Auto-fix
make backend-format

# Type check
make backend-typecheck
```

---

## Frontend Development

### Project Structure

```
frontend/src/
├── app/
│   ├── layout.tsx        Root layout
│   ├── page.tsx          Landing page
│   ├── globals.css       Design system CSS
│   ├── dashboard/        Dashboard route
│   ├── incidents/        Incidents route
│   ├── privacy/          Privacy policy
│   └── terms/            Terms of use
├── components/
│   ├── layout/           Layout components (Sidebar, etc.)
│   └── ui/               Reusable UI components
└── lib/
    └── api.ts            Backend API client
```

### Design Rules (enforced)

- No purple gradients
- No pill-shaped buttons (border-radius: 3-6px max)
- No fake metrics
- No AI-generated imagery
- No cursor animations
- No excessive scroll animations
- Semantic colors only (success=green, warning=amber, critical=red)
- Sharp, functional visual language

### API Client

All backend calls go through `src/lib/api.ts`. Add new typed methods there.

---

## Database Operations

```bash
# Apply all pending migrations
make db-migrate

# Roll back last migration
make db-rollback

# Create new migration after model changes
make db-revision MSG="add telemetry_raw table"

# View migration history
make db-history

# Open psql shell
make db-shell
```

---

## Kafka Operations

Topics are not auto-created (KAFKA_AUTO_CREATE_TOPICS_ENABLE=false).
Phase 2 will add a topic initialization script.

To inspect Kafka (using kafka container):
```bash
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list
```

---

## Troubleshooting

### Services not starting

```bash
docker compose ps          # Check container status
docker compose logs postgres   # Check specific service
```

### Database connection errors

Ensure `POSTGRES_PASSWORD` in `.env` matches the password set when the container was first created.
If you changed the password after creation:
```bash
make docker-clean          # Destroys data
make dev-up
make db-migrate
```

### Port conflicts

All services bind to `127.0.0.1`. If ports are in use:
```bash
netstat -ano | findstr :5432   # Windows - find process on port 5432
```

---

## Code Standards

- Python: type hints required on all functions
- Python: docstrings on all public functions and classes
- Python: no hardcoded credentials or secrets
- Python: structured logging via `get_logger(__name__)` - no `print()`
- TypeScript: strict mode enabled
- All UI copy: no em-dashes, no marketing fluff, precise language
- All metrics: labeled as measured/experimental/assumption/target
