# Development

## Start the Stack

```bash
docker compose up --build
```

No `.env` file is required for local startup. Use `.env.example` as the reference when overriding defaults.

Application settings are read through Pydantic Settings in the backend. Keep new backend configuration in `backend/app/core/config.py`, document it in `.env.example`, and avoid direct `os.getenv` usage outside the settings layer.

## Useful Commands

```bash
make up
make config
make logs
make down
```

## Code Quality

Install and activate pre-commit hooks:

```bash
pip install -e backend[dev]
npm install --prefix frontend
pre-commit install
```

The hooks run Black, isort, Ruff, Prettier, and ESLint. EditorConfig covers Python, TypeScript, JSON, YAML, and Markdown.

Backend-only commands:

```bash
cd backend
pip install -e ".[dev]"
black --check app tests
isort --check-only app tests
ruff check app tests
mypy app
pytest
```

The backend type-check command is `mypy app`.

Frontend commands:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

## Database Migrations

Run Alembic from the backend directory:

```bash
alembic upgrade head
alembic downgrade -1
alembic downgrade base
```

`downgrade base` is destructive and should be used only with disposable local or test databases.

## Docker Verification

Validate Compose and wait for service healthchecks:

```bash
docker compose config
docker compose up --build --wait
docker compose ps
```

## Organization Core Endpoints

The Organization Core module is available under `/api/v1` and requires a Bearer access token with the matching `*.read` or `*.manage` permission:

- `/organizations`
- `/departments`
- `/positions`
- `/employees`

Each collection supports `page`, `page_size`, `sort_by`, and `sort_direction`. Additional filters are available for organization, department, position, employee status, active state, codes, names, and ownership links.

## Inventory Development Notes

The inventory module lives in `backend/app/modules/inventory/` and follows the same layering as Organization Core:

- `domain` for enums and domain language
- `application` for use cases, validation, posting, cancellation, and scope enforcement
- `infrastructure` for SQLAlchemy models and repositories
- `presentation` for thin FastAPI routes and schemas

Database changes are in `20260717_0004_inventory.py`. The migration creates inventory tables, site/warehouse user scope tables, seeds inventory permissions, adds warehouse role templates, and inserts initial Kyiv/Talne sites, common units, and optional main warehouses for existing organizations only when missing.

Run the migration verification from `backend`:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Inventory posting and cancellation must remain atomic through the Unit of Work. A failed post must rollback movements and stock-balance changes.

## Identity & Access

Apply migrations before first local use, then sign in with the bootstrap administrator from `.env` or the Compose defaults:

```bash
cd backend
alembic upgrade head
```

Important local settings:

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_SECRET_KEY`
- `AUTH_ACCESS_TOKEN_MINUTES`
- `AUTH_REFRESH_TOKEN_DAYS`
- `AUTH_FAILED_LOGIN_LIMIT`
- `AUTH_LOCK_MINUTES`
- `AUTH_COOKIE_SECURE`
- `AUTH_COOKIE_SAMESITE`

Identity endpoints:

- `/auth/login`
- `/auth/refresh`
- `/auth/logout`
- `/auth/change-password`
- `/auth/sessions`
- `/users`
- `/roles`
- `/permissions`

Ukrainian administration instructions are in `docs/UserAdministration.uk.md`.

## Logs

Local backend logging is configured by `logging.yaml`. Runtime log files are written to `logs/`; only `logs/.gitkeep` is committed.

## Localization Rules

- Default locale: `uk-UA`
- Timezone: `Europe/Kyiv`
- Date format: `DD.MM.YYYY`
- Time format: 24-hour
- First day of week: Monday

Keep code, routes, database tables, and variables in English. Keep all UI labels, buttons, validation messages, notifications, and dialogs localized.
