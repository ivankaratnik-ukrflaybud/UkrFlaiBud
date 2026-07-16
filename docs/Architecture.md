# UKRFLYBUD ERP Architecture

This document is the single source of truth for the architecture of UKRFLYBUD Manager, a modular ERP platform for construction, manufacturing, warehouse, procurement, documents, tasks, calendar, reporting, and operational management.

## 1. Vision

UKRFLYBUD Manager is designed as a long-lived enterprise application, not a demo or short-term tool. The system must support many iterations, multiple business domains, future integrations, and controlled growth without turning into a tightly coupled monolith.

The product vision is to provide one operational workspace for:

- managing organizations, employees, roles, and access;
- planning and tracking tasks, schedules, and calendar events;
- managing documents and structured approvals;
- maintaining products, bills of materials, stock, procurement, and production flows;
- generating operational and management reports;
- supporting future ERP modules without rewriting the foundation.

The architecture must optimize for clarity, maintainability, testability, Ukrainian-first user experience, and secure enterprise-grade evolution.

## 2. Architectural Principles

- Modular by domain: each ERP area owns its business rules, services, data access, and API surface.
- Clean Architecture: business logic must not depend on frameworks, HTTP, SQLAlchemy sessions, or UI implementation details.
- Explicit boundaries: API, application services, repositories, database models, domain models, and schemas are separate concerns.
- Dependency inversion: higher-level business rules depend on abstractions, not infrastructure details.
- Configuration from environment: runtime settings are read through Pydantic Settings and documented in `.env.example`.
- Ukrainian-first UI: all user-facing text is Ukrainian by default; source code identifiers remain English.
- Infrastructure as code: local services run through Docker Compose and are fronted by Nginx.
- Testability from the beginning: domain and service logic must be testable without running the full stack.
- PostgreSQL only: the platform standard database is PostgreSQL.
- Docker first: every sprint must preserve a working Docker build and startup path.

## 3. Project Rules

These rules are mandatory for all future implementation work:

- Primary application language: Ukrainian.
- Code language: English.
- Use UUID identifiers everywhere for persisted business entities.
- Docker first: local development, verification, and sprint acceptance must work through Docker.
- PostgreSQL only: no alternative production database engines.
- Clean Architecture is required.
- The backend is a Modular Monolith, not microservices.
- The frontend uses Material UI.
- The frontend uses React 19.
- The backend uses FastAPI.
- Routers must not contain business logic.
- The Repository Pattern is required for persistence access.
- Soft delete is required for business records unless a documented exception exists.
- Auditability is required for sensitive and business-critical changes.
- Tests are mandatory for new behavior.
- Every sprint must pass Docker build.

## 4. Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/              HTTP routers, request dependencies, API versioning
│   │   ├── core/             settings, logging, application-wide configuration
│   │   ├── database/         SQLAlchemy engine, sessions, Alembic migrations
│   │   ├── middleware/       FastAPI middleware
│   │   ├── models/           domain model foundations and future domain objects
│   │   ├── repositories/     repository contracts and persistence adapters
│   │   ├── schemas/          Pydantic request/response schemas
│   │   ├── services/         application services and use cases
│   │   └── utils/            technical helpers only
│   └── tests/                backend tests
├── frontend/
│   └── src/
│       ├── components/       reusable UI components
│       ├── features/         feature-level frontend modules
│       ├── hooks/            reusable React hooks
│       ├── layouts/          page shells and layout primitives
│       ├── locales/          i18n resources
│       ├── pages/            route-level pages
│       ├── services/         API clients, i18n, query client, locale utilities
│       ├── theme/            Material UI theme
│       └── types/            shared frontend types
├── docker/                   Nginx, PostgreSQL, pgAdmin configuration
├── docs/                     project documentation
├── logs/                     local runtime logs
├── scripts/                  operational scripts
├── docker-compose.yml
├── logging.yaml
├── Makefile
└── README.md
```

## 5. Modular Architecture

UKRFLYBUD ERP is organized around business modules. A module is a cohesive domain area with its own use cases, rules, repository interfaces, persistence mappings, API routes, UI feature surfaces, and permissions.

Planned backend module shape:

```text
backend/app/modules/<module>/
├── domain/             entities, value objects, domain services
├── application/        use cases, commands, queries, ports
├── infrastructure/     SQLAlchemy repositories, external adapters
└── presentation/       API routers and schemas for the module
```

The current repository has a simplified root-layer skeleton. As modules mature, domain-specific code should move into the module shape above while shared cross-cutting infrastructure remains under `core`, `database`, `middleware`, and `utils`.

Planned ERP modules:

- Identity and RBAC
- Organizations
- Tasks
- Calendar
- Notifications
- Documents
- Products
- BOM
- Warehouse
- Procurement
- Production
- Reporting

## 6. Clean Architecture

The backend follows Clean Architecture with inward dependencies:

```text
API / Presentation
  -> Application Services / Use Cases
    -> Domain Models and Domain Rules
    -> Repository Interfaces
      <- Infrastructure Repository Implementations
      <- Database Models and SQLAlchemy
```

Rules:

- Domain code must not import FastAPI, SQLAlchemy sessions, Pydantic transport schemas, or framework-specific objects.
- Application services coordinate use cases and depend on repository interfaces.
- Infrastructure implements repositories and external integrations.
- API routers translate HTTP requests into use case calls and return response schemas.
- Database models are persistence details, not the domain model itself.

## 7. Backend Layers

### API Layer

Responsibilities:

- HTTP routing and versioning
- request parsing
- response formatting
- dependency injection
- status codes
- API error mapping

The API layer must stay thin. It must not contain business workflows.

### Schemas Layer

Responsibilities:

- Pydantic request and response DTOs
- input shape validation
- API serialization

Schemas are transport contracts. They are not domain entities.

### Services Layer

Responsibilities:

- use case orchestration
- transaction boundaries
- calling repositories and domain services
- enforcing application-level workflows

Services must be easy to unit test with fake repositories.

### Repository Layer

Responsibilities:

- abstract persistence contracts
- SQLAlchemy implementations
- query composition
- mapping between persistence records and domain models

Repository interfaces should be owned by the application/domain side. Concrete implementations belong to infrastructure.

### Database Layer

Responsibilities:

- SQLAlchemy engine and session factory
- declarative base
- Alembic migrations
- persistence model definitions

Database migrations must be the source of truth for schema changes.

### Domain Models

Responsibilities:

- entities
- value objects
- domain invariants
- domain services where needed

Domain models must be framework-independent.

### Middleware and Utilities

Middleware may handle request IDs, structured logging, CORS, metrics, and future security concerns. Utilities must remain technical and must not become a place for hidden business logic.

## 8. Frontend Architecture

The frontend is a React 19, TypeScript, Vite application using Material UI, React Router, TanStack Query, and i18n.

Frontend principles:

- UI text is localized; no hardcoded user-facing copy in components.
- Pages are route-level compositions.
- Features contain domain-specific UI logic.
- Components are reusable and presentation-focused.
- Services own API access, query clients, i18n, and locale utilities.
- Material UI theme defines the design foundation.
- TanStack Query owns server-state caching, retries, loading states, and invalidation.
- React Router owns route composition and navigation.

Planned frontend module shape:

```text
frontend/src/features/<feature>/
├── api/          feature API calls and query keys
├── components/   feature-specific UI
├── hooks/        feature-specific hooks
├── pages/        feature route pages where useful
├── types/        feature DTOs and view models
└── utils/        feature-local helpers
```

Localization rules:

- Default locale: `uk-UA`
- Timezone: `Europe/Kyiv`
- Date format: `DD.MM.YYYY`
- Time format: 24-hour
- First day of week: Monday
- Source identifiers remain English.

## 9. Identity and RBAC

Identity and RBAC will define users, roles, permissions, sessions, and access policies. Authentication and authorization are intentionally not part of the initial infrastructure sprint, but the architecture must reserve clear boundaries.

Planned responsibilities:

- user identity
- login sessions and token strategy
- password and credential policy
- roles and permissions
- organization-scoped access
- module-level permissions
- audit-friendly permission changes

RBAC model:

- Permission: atomic action such as `tasks.read` or `warehouse.adjust_stock`
- Role: named collection of permissions
- User assignment: role assigned to a user in an organization context
- Policy check: application service or API dependency verifies access before executing use cases

Authorization must be centralized and testable. Business services must receive an actor context rather than reading global request state.

## 10. Organizations

Organizations represent the business entities using the ERP.

Planned capabilities:

- company profile
- departments
- teams
- employees and contractors
- organization settings
- organization-specific RBAC

Most operational entities should be organization-scoped. Cross-organization access must be explicit and protected.

## 11. Tasks

The tasks module coordinates operational work across ERP areas.

Planned capabilities:

- task creation
- assignment
- status workflow
- priorities
- due dates
- comments
- attachments
- links to projects, documents, procurement, warehouse, or production records

Tasks must remain generic enough to support multiple domains while allowing domain modules to create or reference tasks.

## 12. Calendar

The calendar module provides scheduling and time-based planning.

Planned capabilities:

- events
- reminders
- task due dates
- production schedules
- procurement delivery dates
- warehouse planning dates
- organization calendars

Calendar data must respect `Europe/Kyiv` timezone by default. Stored timestamps should use timezone-aware values.

## 13. Notifications

Notifications deliver system and workflow updates.

Planned capabilities:

- in-app notifications
- email notification adapters
- event-driven notification generation
- notification read/unread state
- user notification preferences

Notification generation should be triggered by application events, not scattered directly through business workflows.

## 14. Documents

The documents module manages files, metadata, and document workflows.

Planned capabilities:

- document records
- file metadata
- versioning
- document categories
- approvals
- attachments to tasks, procurement, warehouse, production, and organizations
- audit trail

Binary storage must be abstracted behind an interface so local filesystem, S3-compatible storage, or another provider can be introduced later.

## 15. Products

Products describe materials, finished goods, components, and service items used across procurement, warehouse, production, and reporting.

Planned capabilities:

- product catalog
- SKU or internal code
- unit of measure
- categories
- product attributes
- active/inactive state
- supplier references

Product definitions should be stable and reusable across modules.

## 16. BOM

BOM means Bill of Materials. It defines how products are composed from components.

Planned capabilities:

- BOM header
- BOM lines
- component quantities
- unit conversion
- versioning
- effective dates
- approval status

BOM is used by production planning, procurement forecasting, and warehouse reservation.

## 17. Warehouse

The warehouse module manages stock, locations, movements, reservations, and inventory operations.

Planned capabilities:

- warehouses
- storage locations
- stock balances
- inbound movements
- outbound movements
- transfers
- adjustments
- reservations
- inventory counts

Stock-changing operations must be transactional and auditable. Direct stock mutation outside warehouse services is not allowed.

## 18. Procurement

Procurement manages supplier purchasing workflows.

Planned capabilities:

- suppliers
- purchase requests
- purchase orders
- order statuses
- expected delivery dates
- receipts
- supplier documents
- links to warehouse inbound operations

Procurement should integrate with products, warehouse, documents, tasks, and reporting.

## 19. Production

Production manages manufacturing or assembly workflows.

Planned capabilities:

- production orders
- work orders
- BOM consumption
- planned quantities
- actual quantities
- material reservations
- completion records
- production status workflow

Production must integrate with BOM, products, warehouse, tasks, calendar, documents, and reporting.

## 20. Reporting

Reporting provides operational and management insights.

Planned capabilities:

- task reports
- procurement reports
- warehouse stock reports
- inventory valuation
- production reports
- document status reports
- organization-level dashboards

Reporting queries may require read-optimized models in later sprints. Reporting must not compromise transactional domain boundaries.

## 21. UAV Production Lifecycle

The canonical operational lifecycle for UAV production is:

```text
UAV
  -> Model
  -> Specification
  -> Components
  -> Assembly
  -> Testing
  -> Passport
  -> Shipment
```

Ukrainian UI labels for this lifecycle:

```text
БпЛА
  -> Модель
  -> Специфікація
  -> Комплектуючі
  -> Складання
  -> Випробування
  -> Паспорт
  -> Відвантаження
```

Architectural mapping:

- `UAV`: top-level product category or finished product family.
- `Model`: product model definition with versioned technical identity.
- `Specification`: approved technical specification for a model.
- `Components`: BOM-backed list of required parts, materials, and assemblies.
- `Assembly`: production workflow that consumes reserved components and creates a finished unit.
- `Testing`: quality-control workflow with recorded results and pass/fail status.
- `Passport`: generated or attached document package for the finished unit.
- `Shipment`: outbound logistics and warehouse movement for delivery.

Module ownership:

- Products own UAV and model catalog definitions.
- BOM owns component structure and quantities.
- Documents own specifications, passports, attachments, and approval artifacts.
- Warehouse owns component reservations, stock movements, and shipment movements.
- Production owns assembly and testing workflows.
- Tasks and Calendar may coordinate operational work across all lifecycle steps.
- Reporting reads lifecycle state without owning the transactional process.

Rules:

- Every persisted lifecycle entity must use UUID identifiers.
- Lifecycle transitions must be auditable.
- Component consumption and shipment must go through warehouse services.
- Assembly and testing business rules must live in application/domain services, never in routers.
- Data access must go through repositories.
- UI labels for the lifecycle must be localized and displayed in Ukrainian.

## 22. API Standards

### Versioning

All public API routes must be versioned:

```text
/api/v1/...
```

### Naming

- Paths use kebab-case where appropriate.
- JSON fields use snake_case unless frontend conventions require a documented exception.
- Database identifiers use snake_case.
- Source code identifiers use English.

### Response Shape

Simple endpoints may return direct resource DTOs. Collection endpoints should eventually standardize pagination metadata:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 0
}
```

### Errors

API errors should use a consistent shape:

```json
{
  "code": "domain_error_code",
  "message": "Localized or client-displayable message",
  "details": {}
}
```

Internal errors must not expose stack traces or secrets.

### Validation

Input validation belongs to Pydantic schemas for transport shape and to domain/application services for business rules.

### Idempotency

Mutating operations that can be retried by clients or integrations should support idempotency keys in later sprints.

## 23. Security

Security requirements:

- no secrets committed to the repository;
- configuration documented in `.env.example`;
- runtime settings loaded through Pydantic Settings;
- password storage must use modern adaptive hashing when identity is implemented;
- authorization checks must be centralized and covered by tests;
- CORS must be explicit;
- audit logs are required for sensitive business operations;
- file uploads must validate type, size, and storage policy;
- API errors must avoid leaking implementation details;
- production deployment must use TLS;
- database credentials must be managed outside source control.

Future hardening:

- rate limiting;
- request IDs;
- structured audit logging;
- dependency vulnerability scanning;
- SAST and container image scanning in CI.

## 24. Testing Strategy

Testing must grow with the system.

### Backend

- Unit tests for domain models and value objects
- Unit tests for application services using fake repositories
- Repository tests against test PostgreSQL
- API tests through FastAPI test client
- Migration tests for Alembic
- Security tests for authorization decisions once RBAC exists

### Frontend

- Unit tests for utilities and hooks
- Component tests for reusable UI
- Feature tests for module flows
- Integration tests for route-level pages
- Accessibility checks for key workflows
- i18n coverage to prevent missing Ukrainian labels

### End-to-End

E2E tests should cover critical business flows after modules exist:

- identity and login
- task lifecycle
- procurement-to-warehouse flow
- production order flow
- reporting views

### CI Expectations

CI should eventually run:

- backend lint and tests
- frontend lint, typecheck, and tests
- Docker build
- migration checks
- security scans

## 25. Deployment

Current infrastructure is local-development oriented:

- Docker Compose
- PostgreSQL 16
- pgAdmin
- FastAPI backend
- Vite frontend
- Nginx reverse proxy

Production deployment must add:

- production-grade backend image target;
- static frontend build served by Nginx or CDN;
- managed PostgreSQL or hardened PostgreSQL deployment;
- TLS certificates;
- secret management;
- backups and restore procedures;
- logging and metrics aggregation;
- healthcheck monitoring;
- CI/CD pipeline;
- environment-specific configuration;
- zero-downtime migration strategy where possible.

## 26. Observability

Observability foundation:

- application logs through `logging.yaml`;
- local logs written under `logs/`;
- container healthchecks in Docker Compose;
- future request IDs and structured logs;
- future metrics endpoint;
- future tracing for cross-module workflows.

## 27. Roadmap

### Sprint 1: Infrastructure Foundation

- Monorepo structure
- Docker Compose stack
- FastAPI backend skeleton
- React frontend skeleton
- PostgreSQL, pgAdmin, Nginx
- `.env.example`
- logging foundation
- healthchecks
- VS Code workspace settings
- pre-commit and formatting tools

### Sprint 2: Core Backend Foundation

- module folder pattern
- base repository contracts
- transaction management
- shared error model
- API error responses
- request ID middleware
- initial test setup

### Sprint 3: Identity and RBAC

- user model
- authentication flow
- roles and permissions
- organization-scoped access
- authorization dependencies
- security tests

### Sprint 4: Organizations

- organization profile
- departments
- team structure
- employee records foundation
- organization settings

### Sprint 5: Tasks

- task model
- assignment
- statuses and priorities
- comments
- task API
- task UI

### Sprint 6: Calendar

- calendar events
- task due date integration
- reminders foundation
- Ukrainian date/time behavior
- calendar UI

### Sprint 7: Notifications

- notification model
- in-app notification center
- event-driven notification triggers
- notification preferences

### Sprint 8: Documents

- document records
- file metadata
- upload abstraction
- versioning foundation
- document attachments
- approval workflow foundation

### Sprint 9: Products

- product catalog
- units of measure
- product categories
- supplier references
- product API and UI

### Sprint 10: BOM

- BOM headers and lines
- BOM versioning
- component quantities
- effective dates
- approval status

### Sprint 11: Warehouse

- warehouses and locations
- stock balances
- movements
- transfers
- adjustments
- reservations
- inventory counts

### Sprint 12: Procurement and Production

- suppliers
- purchase requests
- purchase orders
- receipts
- production orders
- BOM consumption
- material reservations
- completion records

### Sprint 13: Reporting and Hardening

- operational dashboards
- warehouse reports
- procurement reports
- production reports
- audit reporting
- performance review
- security hardening
- deployment readiness

## 28. Non-Goals for the Infrastructure Sprint

The infrastructure sprint must not implement:

- authentication;
- authorization;
- users;
- tasks;
- calendar workflows;
- ERP business logic;
- production workflows;
- procurement workflows;
- warehouse stock mutation;
- reporting logic.

Only architecture, configuration, infrastructure, and project skeleton are in scope for Sprint 1.
