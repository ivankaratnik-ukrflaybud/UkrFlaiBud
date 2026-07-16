# Deployment

This repository currently contains local-development infrastructure only. Production deployment should add:

- Separate production Dockerfiles or multi-stage targets
- External secret management
- Managed PostgreSQL or hardened database hosting
- TLS termination
- Observability, log aggregation, and backups
- CI checks for backend, frontend, migrations, and container builds

The current Compose stack is suitable for local development and infrastructure validation.

