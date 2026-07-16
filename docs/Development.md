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

## Logs

Local backend logging is configured by `logging.yaml`. Runtime log files are written to `logs/`; only `logs/.gitkeep` is committed.

## Localization Rules

- Default locale: `uk-UA`
- Timezone: `Europe/Kyiv`
- Date format: `DD.MM.YYYY`
- Time format: 24-hour
- First day of week: Monday

Keep code, routes, database tables, and variables in English. Keep all UI labels, buttons, validation messages, notifications, and dialogs localized.
