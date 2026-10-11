# GOAG Local Setup Instructions

This guide sets up a fresh local checkout of GOAG V1, including the API, database, frontend, seeded users, and browser tests.

## 1. Prerequisites

Install the following before starting:

- Node.js 20 or newer
- pnpm
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop or another Docker Engine
- A Supabase development project for authentication

Check the tools:

```bash
node --version
pnpm --version
python --version
uv --version
docker --version
```

## 2. Clone and configure the repository

```bash
git clone https://github.com/samad-012/goag.git
cd goag
cp .env.example .env
```

Open `.env` and replace the Supabase placeholder values:

```text
SUPABASE_URL=<your Supabase project URL>
SUPABASE_ANON_KEY=<your Supabase anon key>
SUPABASE_JWT_SECRET=<your development JWT secret>
NEXT_PUBLIC_SUPABASE_URL=<your Supabase project URL>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your Supabase anon key>
```

The default local database URL expects the PostgreSQL container supplied by this repository:

```text
DATABASE_URL=postgresql+psycopg://goag:goag@localhost:5432/goag
```

Never commit `.env`. It is ignored by Git. Do not use the development password outside a local development environment.

## 3. Start PostgreSQL

From the repository root:

```bash
docker compose up postgres -d
```

Check that the database is running:

```bash
docker compose ps
```

## 4. Install and initialize the API

```bash
cd apps/api
uv sync --extra dev
uv run alembic upgrade head
uv run python seed.py
uv run python seed_users.py
```

The seed scripts create the GOAG company, roles, permissions, component catalog, drone model, and invited application users.

Start the API in this terminal:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The API health endpoint is available at [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz).

## 5. Create local Supabase Auth users

`seed_users.py` creates application users but does not create Supabase Auth accounts. In the Supabase dashboard, create email/password users with these addresses:

| Role | Email | Local password |
| --- | --- | --- |
| Managing Director | `md@goag.example` | `123456` |
| Production Manager | `production.manager@goag.example` | `123456` |
| Store Manager | `store.manager@goag.example` | `123456` |
| Sales Manager | `sales.manager@goag.example` | `123456` |
| Technician | `technician@goag.example` | `123456` |
| After-Sales Manager | `after.sales@goag.example` | `123456` |

Use these credentials only with a local development Supabase project. The first successful authenticated API request links the Supabase identity to the matching seeded application user.

## 6. Install and start the frontend

Open a second terminal at the repository root:

```bash
pnpm install
pnpm web:dev
```

Open [http://localhost:3000/login](http://localhost:3000/login).

## 7. Run quality checks

From the repository root:

```bash
pnpm run web:lint
pnpm run typecheck
pnpm run web:build
```

Run API checks:

```bash
cd apps/api
uv run ruff check app tests
uv run pytest -q
```

## 8. Run browser tests

Playwright starts the API and frontend servers automatically. Run the seeded six-role matrix with the local credentials:

```bash
cd <repository-root>
GOAG_RUN_ROLE_MATRIX=1 \
GOAG_TEST_PASSWORD=123456 \
GOAG_TEST_MD_PASSWORD=123456 \
GOAG_TEST_MD_EMAIL=md@goag.example \
pnpm exec playwright test apps/web/tests/role-matrix.spec.ts
```

Run the read-only failure-state tests:

```bash
GOAG_E2E_FAILURES=1 \
GOAG_TEST_PASSWORD=123456 \
GOAG_TEST_STORE_MANAGER_EMAIL=store.manager@goag.example \
pnpm exec playwright test apps/web/tests/failure-state.spec.ts
```

Run the proxy-timeout test with its dedicated configuration:

```bash
GOAG_E2E_PROXY_TIMEOUT=1 \
GOAG_TEST_PASSWORD=123456 \
GOAG_TEST_STORE_MANAGER_EMAIL=store.manager@goag.example \
pnpm exec playwright test --config=playwright.proxy-timeout.config.ts
```

The serialized production workflow test writes data to the database. Run it only against an isolated development database:

```bash
GOAG_E2E_WORKFLOW=1 \
GOAG_TEST_PASSWORD=123456 \
pnpm exec playwright test apps/web/tests/workflow-e2e.spec.ts
```

## 9. Common problems

### `password authentication failed` or database connection refused

Start PostgreSQL and confirm that `.env` contains the local database URL:

```bash
docker compose up postgres -d
```

### Login returns an authentication error

Confirm that the Supabase URL and anon key are valid, the Auth user exists with the exact seeded email, and the user password is correct.

### Browser tests are skipped

The role, failure-state, proxy, and workflow suites are opt-in. Set the corresponding environment variable shown in the browser-test commands above.

### Port already in use

The local defaults are API port `8000` and frontend port `3000`. Stop the process using the port before starting the dev servers, or update the local environment and Playwright configuration consistently.

## 10. Security reminders

- Keep `.env` private and never commit it.
- Use a separate Supabase project for staging or production.
- Never deploy `GOAG_TEST_PASSWORD=123456`.
- Do not run the workflow browser test against shared or production data.
