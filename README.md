# GOAG V1

This repository contains the GOAG V1 technical foundation.

## Current implementation

- Next.js web scaffold with Supabase SSR authentication entry points.
- FastAPI API scaffold with Supabase JWT verification, current-user endpoint, RBAC dependencies, Managing Director user administration, and audit logging.
- Alembic initial migration for identity, memberships, roles, permissions, registered devices, and audit events.
- Seed script for the approved GOAG roles and permissions.
- Docker Compose local PostgreSQL, API, and worker services.
- Foundation tests for health, current-user, role permission, user creation, and audit logging.

## Local setup

1. Copy `.env.example` to `.env` and provide Supabase development values.
2. Start PostgreSQL: `docker compose up postgres -d`.
3. Install API dependencies: `cd apps/api && uv sync --extra dev`.
4. Run migrations: `uv run alembic upgrade head`.
5. Seed roles and the component catalog: `uv run python seed.py`.
6. Seed standard development users: `uv run python seed_users.py`. These are invited application users; create their Supabase Auth accounts, then the first authenticated request with a matching email links the Auth subject automatically.
7. Run tests: `uv run pytest`.
8. Start the API: `uv run uvicorn app.main:app --reload`.
9. Install web dependencies: `pnpm --dir apps/web install`.
10. Start the web app: `pnpm web:dev`.

The actual Supabase project, authentication provider settings, and production hosting are intentionally configured through environment variables rather than committed credentials.
