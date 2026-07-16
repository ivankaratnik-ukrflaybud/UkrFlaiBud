# Architecture

UKRFLYBUD Manager is organized as a monorepo with independently buildable backend and frontend applications plus shared local infrastructure.

## Backend

The backend follows clean architecture boundaries:

- `api`: HTTP routers, request dependencies, and transport-specific code
- `services`: application use cases and orchestration
- `repositories`: persistence ports and repository contracts
- `database`: SQLAlchemy engine, sessions, base metadata, and Alembic migrations
- `models`: framework-independent domain model foundations
- `schemas`: Pydantic transport schemas
- `middleware`: HTTP middleware
- `utils`: technical helpers

Business logic must not import FastAPI, SQLAlchemy sessions, or other framework adapters directly.

## Frontend

The frontend is a React 19 application with Material UI, React Router, TanStack Query, and i18n initialized from the first commit. Source identifiers remain English, while all user-facing interface copy is Ukrainian by default.

## Infrastructure

Docker Compose starts PostgreSQL 16, pgAdmin, the FastAPI backend, the Vite frontend, and Nginx as the local reverse proxy.

