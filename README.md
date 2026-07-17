# UKRFLYBUD Manager

UKRFLYBUD Manager is a production-oriented ERP platform skeleton for long-term enterprise development. The current scope includes reusable core platform foundations, Identity & Access, Organization Core, and the Warehouse & Item Catalog inventory foundation.

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

Frontend-only checks can be run from the frontend directory:

```bash
npm run lint
npm run typecheck
npm test
npm run build
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

## Identity & Access

Local bootstrap settings create the first administrator and system RBAC templates:

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_SECRET_KEY`
- `AUTH_ACCESS_TOKEN_MINUTES`
- `AUTH_REFRESH_TOKEN_DAYS`
- `AUTH_FAILED_LOGIN_LIMIT`
- `AUTH_LOCK_MINUTES`

Refresh tokens are stored in HttpOnly cookies. Access tokens are short-lived and sent as Bearer tokens by the frontend.

Identity endpoints are available under `/api/v1`:

- `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/logout-all`, `GET /auth/me`, `POST /auth/change-password`, `GET /auth/sessions`
- `GET /users`, `POST /users`, `GET /users/{id}`, `PATCH /users/{id}`, `DELETE /users/{id}`, `POST /users/{id}/reset-password`, `PUT /users/{id}/roles`
- `GET /roles`, `POST /roles`, `GET /roles/{id}`, `PATCH /roles/{id}`, `DELETE /roles/{id}`, `PUT /roles/{id}/permissions`
- `GET /permissions`

See `docs/UserAdministration.uk.md` for Ukrainian user administration steps.

Inventory scope endpoints extend user administration:

- `GET /identity/users/{id}/inventory-scope`
- `PUT /identity/users/{id}/inventory-scope`

## Organization Core API

The first business module exposes these versioned endpoints:

- `POST /api/v1/organizations`, `GET /api/v1/organizations`, `GET /api/v1/organizations/{id}`, `PATCH /api/v1/organizations/{id}`, `DELETE /api/v1/organizations/{id}`
- `POST /api/v1/departments`, `GET /api/v1/departments`, `GET /api/v1/departments/{id}`, `PATCH /api/v1/departments/{id}`, `DELETE /api/v1/departments/{id}`
- `POST /api/v1/positions`, `GET /api/v1/positions`, `GET /api/v1/positions/{id}`, `PATCH /api/v1/positions/{id}`, `DELETE /api/v1/positions/{id}`
- `POST /api/v1/employees`, `GET /api/v1/employees`, `GET /api/v1/employees/{id}`, `PATCH /api/v1/employees/{id}`, `DELETE /api/v1/employees/{id}`

List endpoints support pagination, filtering, and sorting. Update requests require the current `version` for optimistic concurrency.

## Warehouse & Item Catalog API

Sprint 5 adds the inventory foundation under `/api/v1/inventory`:

- Sites, warehouses, storage locations, units, categories, items
- Lots and serial numbers
- Inventory documents and document lines
- Posting, cancellation with reversal movements, stock balances, movement ledger, low-stock queries

Warehouse access is enforced on the backend through permissions plus site/warehouse scope. The immutable `inventory_movements` ledger is the source of truth; `inventory_stock_balances` is maintained transactionally for current stock queries.

User guides:

- `docs/WarehouseAdministration.uk.md`
- `docs/WarehouseOperations.uk.md`
- `docs/InventoryArchitecture.md`

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

Procurement, suppliers, BOM, manufacturing orders, CNC jobs, production consumption, assembly, accounting valuation, invoices, and financial accounting are intentionally not implemented yet.
