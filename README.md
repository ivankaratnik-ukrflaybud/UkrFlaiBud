# UKRFLYBUD Manager

UKRFLYBUD Manager is a production-oriented ERP platform skeleton for long-term enterprise development. The current scope includes reusable core platform foundations plus the Organization Core module for organizations, departments, positions, and employees.

## Stack

- Backend: Python 3.13, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Uvicorn
- Frontend: React 19, TypeScript, Vite, Material UI, React Router, TanStack Query
- Database: PostgreSQL 16
- Infrastructure: Docker, Docker Compose, Nginx, pgAdmin

## Run Locally

```bash
docker compose up --build
```

The stack uses safe local defaults from `docker-compose.yml`. Application settings are defined in `.env`; copy `.env.example` to `.env` when you need explicit local overrides.

## Local URLs

- Application through Nginx: <http://localhost:8080>
- Backend API: <http://localhost:8000>
- Backend health: <http://localhost:8000/api/v1/health>
- API docs: <http://localhost:8000/docs>
- Frontend dev server: <http://localhost:5173>
- pgAdmin: <http://localhost:5050>

## Code Quality

Pre-commit is configured for automatic formatting and lint fixes:

```bash
pip install -e backend[dev]
npm install --prefix frontend
pre-commit install
```

Run all hooks manually:

```bash
pre-commit run --all-files
```

Backend-only checks can be run from the backend directory:

```bash
pip install -e ".[dev]"
black --check app tests
isort --check-only app tests
ruff check app tests
mypy app
pytest
```

Configured tools:

- Backend: Black, isort, Ruff, mypy, pytest
- Frontend and project config files: Prettier, ESLint
- Editor behavior: `.editorconfig` and `.vscode/`

## Healthchecks and Logs

Docker healthchecks are configured for PostgreSQL, backend, frontend, and Nginx. Backend logs are configured through `logging.yaml` and written to `logs/backend.log` during local development.

Verify Docker configuration and service health:

```bash
docker compose config
docker compose up --build --wait
docker compose ps
```

## Database Migrations

Run migrations from the backend directory:

```bash
alembic upgrade head
alembic downgrade -1
```

Use `alembic downgrade base` only for disposable local or test databases.

## Organization Core API

The first business module exposes these versioned endpoints:

- `POST /api/v1/organizations`, `GET /api/v1/organizations`, `GET /api/v1/organizations/{id}`, `PATCH /api/v1/organizations/{id}`, `DELETE /api/v1/organizations/{id}`
- `POST /api/v1/departments`, `GET /api/v1/departments`, `GET /api/v1/departments/{id}`, `PATCH /api/v1/departments/{id}`, `DELETE /api/v1/departments/{id}`
- `POST /api/v1/positions`, `GET /api/v1/positions`, `GET /api/v1/positions/{id}`, `PATCH /api/v1/positions/{id}`, `DELETE /api/v1/positions/{id}`
- `POST /api/v1/employees`, `GET /api/v1/employees`, `GET /api/v1/employees/{id}`, `PATCH /api/v1/employees/{id}`, `DELETE /api/v1/employees/{id}`

List endpoints support pagination, filtering, and sorting. Update requests require the current `version` for optimistic concurrency.

## Repository Layout

```text
.
├── backend/              FastAPI service and clean backend layers
├── frontend/             React client with Ukrainian-first i18n
├── docker/               Nginx, PostgreSQL, and pgAdmin configuration
├── docs/                 Architecture, development, and deployment notes
├── scripts/              Operational scripts placeholder
├── docker-compose.yml    Local development stack
├── Makefile              Common local commands
└── .env.example          Environment variable reference
```

## Localization

The primary UI language is Ukrainian. The default locale is `uk-UA`, timezone is `Europe/Kyiv`, dates use `DD.MM.YYYY`, time is 24-hour, and Monday is the first day of the week. Source code, API routes, database objects, and variable names remain English.

## Current Scope

Authentication, authorization, users, roles, tasks, warehouse, procurement, production, products, documents, notifications, and unrelated ERP workflows are intentionally not implemented yet.
