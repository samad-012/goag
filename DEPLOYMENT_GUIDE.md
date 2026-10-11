# GOAG Deployment Guide

This guide describes the recommended staging-first deployment for GOAG V1.

## 1. Deployment architecture

| Service | Recommended platform | Purpose |
| --- | --- | --- |
| Next.js frontend | Vercel or an equivalent Node.js host | Browser application and server-side Supabase session handling |
| FastAPI backend | Render Web Service | Protected API, RBAC, inventory, production, attendance, and mailbox endpoints |
| Python worker | Render Background Worker | Future asynchronous jobs; optional until worker jobs are implemented |
| Database and authentication | Supabase | PostgreSQL, Supabase Auth, and Google OAuth |

Use a separate Supabase project for staging. Do not expose the local development database or deploy the local Docker Compose PostgreSQL service as the production database.

## 2. Pre-deployment checklist

Before creating hosted services:

- Push the repository to the Git provider connected to the hosting platforms.
- Create a separate Supabase staging project.
- Confirm the staging frontend hostname and the Render API hostname.
- Generate new staging secrets. Do not reuse development secrets or the shared development password.
- Decide whether Gmail mailbox access is enabled in staging. If enabled, use a staging/test mailbox connection.
- Keep the current local `.env` file private; never commit it.

The current `/purchases` URL is not part of V1. Purchasing and supplier replenishment remain outside the deployed scope.

## 3. Supabase staging setup

In the Supabase staging project:

1. Copy the project URL and public anon key.
2. Copy the database connection string. Use the pooled or direct connection string supported by the selected deployment environment.
3. Configure Auth URL settings:
   - Site URL: the staging frontend URL, for example `https://staging.goag.example`
   - Redirect URL: `https://staging.goag.example/auth/callback`
4. Configure Google OAuth with the staging callback URL required by Supabase.
5. Create staging Auth users for each role that will be tested.
6. Confirm email/password login and Google login work before inviting the wider team.

The application links an invited application user to a matching verified Supabase Auth identity on the first authenticated API request.

## 4. Render FastAPI service

Create a Render **Web Service** connected to the repository.

Recommended settings:

| Setting | Value |
| --- | --- |
| Root directory | `apps/api` |
| Runtime | Docker |
| Dockerfile | `apps/api/Dockerfile` relative to the repository, or the Dockerfile detected from the root directory |
| Docker command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/healthz` |
| Branch | The staging branch |

The current API Dockerfile does not define a production command, so set the Docker command explicitly in the Render service settings. A later hardening task can add the command directly to the Dockerfile.

Render must receive traffic on `0.0.0.0` and the platform-provided `$PORT`; do not use the local `--reload` command.

### FastAPI environment variables

Add these values to the Render Web Service. Use Render's Environment page or an environment group; do not commit secrets.

```text
APP_ENV=staging
API_PORT=10000
SUPABASE_URL=https://<staging-project>.supabase.co
SUPABASE_ANON_KEY=<staging-anon-key>
SUPABASE_JWT_SECRET=<staging-jwt-secret-if-required>
SUPABASE_JWT_AUDIENCE=authenticated
DEVICE_HASH_SECRET=<new-random-secret>
DATABASE_URL=<staging-supabase-postgres-url>
CORS_ORIGINS=https://<staging-frontend-host>
GOAG_WEB_URL=https://<staging-frontend-host>
GOAG_TEST_WORKSITE_LAT=<approved-staging-latitude>
GOAG_TEST_WORKSITE_LON=<approved-staging-longitude>
GOAG_TEST_GEOFENCE_RADIUS_M=150
GOAG_MAX_GPS_ACCURACY_M=100
GOAG_SHIFT_START=09:00
GOAG_SHIFT_END=18:00
GOAG_LATE_GRACE_MINUTES=15
GOAG_TEST_PROXY_DELAY_MS=0
```

If the shared mailbox is enabled in staging, also configure:

```text
GOAG_GMAIL_CLIENT_ID=<staging-google-client-id>
GOAG_GMAIL_CLIENT_SECRET=<staging-google-client-secret>
GOAG_GMAIL_REDIRECT_URI=https://<staging-api-host>/api/v1/email/oauth/callback
GOAG_GMAIL_MAILBOX_ADDRESS=<optional-staging-mailbox>
GOAG_GMAIL_TOKEN_ENCRYPTION_KEY=<new-fernet-key>
```

Keep all Playwright credentials out of the hosted service unless a dedicated staging test service needs them. Never deploy `GOAG_TEST_PASSWORD=123456`.

## 5. Database migration and seed

Run migrations once against the staging Supabase database. Execute from the API directory with the staging environment loaded:

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run python seed.py
```

`seed.py` creates the approved GOAG company, roles, permissions, and catalog data. Do not run development user/password assumptions in production.

Create real staging users in Supabase Auth, then use the application to link them to the approved memberships. Verify each user has the intended role before testing.

## 6. Render worker service

Create a Render **Background Worker** only when there are asynchronous jobs to process.

Recommended settings:

| Setting | Value |
| --- | --- |
| Root directory | `apps/worker` |
| Runtime | Docker |
| Dockerfile | `apps/worker/Dockerfile` |
| Branch | The staging branch |

The current worker is an idle V1 boundary and does not process production jobs yet. It can remain local until the transactional outbox and email-job workflow are implemented.

## 7. Next.js frontend deployment

Create a Next.js deployment connected to the repository.

If using Vercel, set the project root to the repository root and configure the Next.js application in `apps/web` according to the monorepo settings. If using another Node.js host, use the same workspace commands.

Build command:

```bash
pnpm --dir apps/web build
```

Start command for a long-running Node.js host:

```bash
pnpm --dir apps/web start
```

### Frontend environment variables

```text
NEXT_PUBLIC_SUPABASE_URL=https://<staging-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<staging-anon-key>
API_BASE_URL=https://<staging-api-host>/api/v1
```

The frontend's server-side proxy uses `API_BASE_URL` to reach FastAPI. `NEXT_PUBLIC_*` values are intentionally public Supabase client configuration; never put private keys in them.

## 8. OAuth and CORS verification

After both services have stable staging URLs:

1. Add the staging frontend URL to Supabase Auth Site URL/redirect settings.
2. Add the staging callback URL to the Google OAuth client.
3. Set `CORS_ORIGINS` on Render to the exact staging frontend origin, including the scheme and without a trailing route.
4. Set `GOAG_WEB_URL` to the same frontend origin.
5. If Gmail is enabled, set the Gmail OAuth redirect URI to the public Render API URL and re-authorize the shared mailbox.
6. Confirm no localhost URL remains in the hosted environment variables.

## 9. Staging smoke test

Run these checks in order:

1. Open the staging frontend and confirm the professional `/login` screen loads.
2. Sign in with a staging Managing Director account.
3. Confirm `/api/v1/me` returns the expected membership and permissions.
4. Test sign out and sign in again.
5. Test each role's allowed and forbidden dashboard routes.
6. Test team administration as Managing Director.
7. Test opening inventory and serialized component records.
8. Test the production workflow: create drone, request components, partial issue, serial assignment, installation, task completion, and confirmation.
9. Test attendance using staging coordinates and a registered device.
10. Test the shared mailbox only as Managing Director and Store Manager, if enabled.
11. Review Render logs, Supabase Auth logs, audit events, and database records.

For a data-writing Playwright workflow, use a dedicated staging account and data prefix. Do not run it against production data.

## 10. Production release gate

Do not promote staging to production until:

- The staging build and TypeScript checks pass.
- API tests, linting, and isolated Playwright checks pass.
- All six role permissions have been manually verified.
- Real GOAG catalog and opening inventory data are ready.
- The final office coordinates and geofence radius are approved.
- Development passwords are replaced with strong per-user credentials.
- Production Supabase project and production secrets are separate from staging.
- Google OAuth and Gmail settings are configured for the production domain.
- Database backups and a rollback plan are confirmed.
- The Managing Director approves the first pilot release.

## 11. Rollback

If a deployment fails:

1. Stop accepting new operational changes if data integrity could be affected.
2. Use Render's previous successful deploy for the API and frontend.
3. Do not downgrade database migrations automatically. Restore from a backup or apply a reviewed forward migration.
4. Review audit events and Render/Supabase logs.
5. Re-test login and `/healthz` before reopening the staging or production URL.

## Official Render references

- [Deploy a FastAPI app](https://render.com/docs/deploy-fastapi)
- [Health checks](https://render.com/docs/health-checks)
- [Environment variables and secrets](https://render.com/docs/configure-environment-variables)
- [Docker on Render](https://render.com/docs/docker)
- [Background workers](https://render.com/docs/background-workers)
