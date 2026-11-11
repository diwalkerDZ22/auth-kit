# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

`auth-kit` is a reusable authentication module, extracted from the FakeJobApplicationRecognition project (history kept). It must stay project-agnostic: no business logic from a consuming project belongs here.

- `backend/`: FastAPI authentication/authorization service.
- `frontend/`: React + TypeScript (Vite) app. `src/auth/` is the reusable module and must not import from `src/app/` (demo shell).
- `docs/Sprint*.md`: design docs (in French) describing the intended behavior of each sprint; read the relevant one before changing the matching feature.

Code comments, log messages, docs and API error messages are in French. Keep that convention.

## Commands

Run backend commands from `backend/`, because `app` is imported as a top-level package and `.env` is read from the working directory.

```bash
python -m pip install -r requirements.txt
cp .env.example .env            # then fill in SECRET_KEY and RESEND_API_KEY (required, the app won't start without them)
alembic upgrade head            # apply migrations
python scripts/seed_roles.py    # create/sync roles + permissions (needed before any register: create_user requires role "user")
python -m uvicorn app.main:app --reload   # Swagger UI at http://127.0.0.1:8000/docs

alembic revision --autogenerate -m "message"   # after changing app/db/models.py

python -m scripts.test_email you@example.com [--purpose login]   # test a Resend send
python -m scripts.check_link <username>                          # create a verification link for a user by hand
```

Tests: `python -m pip install -r requirements-dev.txt` then `python -m pytest` (from `backend/`). `tests/conftest.py` sets env vars before importing `app` (temporary SQLite DB, fake `SECRET_KEY`), recreates the schema and seeds `user`/`admin` before each test, disables the rate limiter, and replaces `resend.Emails.send` with an in-memory outbox. Helpers: `make_user`, `login` (full email flow), `link_token`, `bearer`. No linter config.

Frontend (from `frontend/`): `npm install`, `npm run dev` (port 5173, proxies `/api/*` to `http://127.0.0.1:8000/*`), `npm run build` (tsc + vite), `npm run lint` (oxlint). Keep build and lint warning-free.

## Frontend architecture

- **Tokens**: the access token lives only in memory (`auth/api.ts`); the refresh token is an httpOnly cookie. Never use localStorage/sessionStorage for tokens. `refreshSession()` is single-flight; `send()` replays a request once after a 401 `invalid_token`; a refresh is scheduled one minute before expiry; logout is broadcast to other tabs (`BroadcastChannel`).
- **Auth state**: `AuthProvider` restores the session with `/auth/refresh` on load, then `/auth/me` via TanStack Query (`ME_QUERY_KEY`). Use `useAuth()` (from `auth/context.ts`) and the guards `RequireAuth`, `RequirePermission`, `GuestOnly`. New pages are added to the router next to `...authRoutes`.
- **Forms**: React Hook Form + Zod (`auth/schemas.ts`, mirrors the backend rules). Show backend errors with `applyApiError()` (`fields` under inputs, the rest in `errors.root`); never duplicate backend messages.
- `tsconfig` uses `verbatimModuleSyntax` and `erasableSyntaxOnly`: `import type` for types, no enums, no constructor parameter properties.

## Backend architecture

- **Config** (`app/core/config.py`): a pydantic-settings `Settings` singleton loaded from `.env`. `DATABASE_URL` may be SQLite or PostgreSQL. `app/db/base.py` rewrites `postgresql://` to `postgresql+psycopg://` and forces `sslmode=require`. `alembic/env.py` takes the DB URL from these settings, not from `alembic.ini`.
- **Routers** (`app/main.py`): `api/auth.py` (logout, `/me`, auth dependencies) and `api/authentification/{login,register}.py` are mounted under `/auth`. `api/authentification/password.py` (forgot / reset) is also under `/auth`. `admin.py` has its own `/admin` prefix (users list/detail/update, roles), guarded by `users:manage`.
- **Auth dependencies** (`api/auth.py`): `get_current_user` decodes the bearer JWT (`sub` = username) → `get_current_active_user` rejects disabled or unverified accounts → `require_permission("code")` is a dependency factory that checks the user's role permissions. Protect new routes with `Depends(require_permission(...))`.
- **Passwords** (`core/password_policy.py`): `password_problem()` / `username_problem()` return a French message or `None`. Schemas raise `PydanticCustomError("kit_...", message)`; `errors.py` passes `kit_*` messages through as-is in `fields`. Routes that need the account (change/reset) raise `ApiError("validation_error", fields={...})` via `api.auth.new_password_error`.
- **Dates**: use `db.types.UTCDateTime` for new datetime columns (always timezone-aware, also on SQLite).
- **Migrations** must run on an empty DB, PostgreSQL and SQLite: use `op.batch_alter_table` for alter/drop/constraints, and guard PostgreSQL-only SQL with `op.get_bind().dialect.name`.
- **RBAC** (`db/models.py`): `User.role_id` points to `Role`, which has many-to-many `Permission` rows via `role_permissions`. Permission codes are strings like `users:manage`. Roles and permissions are declared in `scripts/seed_roles.py` (kit default: `user` with none, `admin` with `users:manage`), which is idempotent and resyncs each role's permissions. A consuming project adds its own permissions there; beware that running it against a DB shared with a project that has extra permissions removes them from the listed roles.
- **Tokens** (`core/security.py`, `core/tokens.py`): access and refresh tokens are both HS256 JWTs signed with the same secret (`SECRET_KEY`, min 32 chars), told apart by `type: "access"` / `type: "refresh"`, each with a random `jti`; `get_current_user` rejects anything but `access`. **Revocation**: tokens carry `ver` = `User.token_version`; a mismatch is `invalid_token`. Call `crud.user.bump_token_version(user)` (or `set_password`, which calls it) whenever sessions must die: logout, password change/reset, admin disable or role change. Only the latest refresh token is stored on `User.refresh_token`, and logout clears it. `issue_tokens()` is the single place where tokens are issued.
- **Email verification, three purposes** (`core/verification.py`, table `email_verifications`, sent through Resend in `core/email.py` as a `BackgroundTask`):
  - `signup`: `/auth/register` creates the user with `is_verified=False` and emails a link (24h). `POST /auth/verify` sets `is_verified`. `/auth/resend-verification` gives the same response whether or not the account exists.
  - `login`: when the password is correct, `/auth/token` does **not** return JWTs. It emails a link (15 min, max 1 per minute) and returns 202 with an `attempt_id`. Clicking the link calls `POST /auth/verify`, which only sets `approved_at`. The original page polls `POST /auth/login/claim` with `attempt_id` and gets the tokens within 2 minutes of approval (`claimed_at`).
  - `reset`: `POST /auth/password/forgot` (generic 200, max 1 mail / 2 min) emails a `FRONTEND_RESET_URL` link (30 min); `POST /auth/password/reset` sets the password, bumps `token_version` and sets `is_verified`. `/auth/verify` only accepts `signup` and `login` links.
  - The login email is sent synchronously: if Resend fails, the pending link is deleted and `/auth/token` returns 503 `email_unavailable`. Signup and reset emails stay `BackgroundTask`s.
  - Only SHA-256 hashes of the link token and of the `attempt_id` are stored. Creating a new link invalidates earlier unused links of the same user and purpose by setting `used_at`.
  - With `LOGIN_EMAIL_REQUIRED=false` (dev only), `/auth/token` returns tokens directly, which makes Swagger testing possible.
- **Refresh cookie** (`core/cookies.py`): `issue_session()` (`core/tokens.py`) returns `AccessToken` in the body and sets the refresh token as an httpOnly cookie (`REFRESH_COOKIE_*`, `COOKIE_SECURE`, `COOKIE_SAMESITE`). `/auth/refresh` and `/auth/logout` read the cookie and require the `X-CSRF-Protection: 1` header (`require_csrf`). The refresh token never appears in a response body.
- **Emails**: `EMAIL_BACKEND=console` (dev only) logs emails, links included, instead of sending them.
- The frontend is expected at `http://localhost:5173` (`CORS_ORIGINS` and `FRONTEND_VERIFY_URL` in settings). `GET /auth/verify` serves a minimal HTML confirm page for testing without the frontend.
- `slowapi` (`core/limiter.py`, per-IP, in-memory) limits every public `/auth/*` POST route with `@limiter.limit(...)`. Rate-limited routes need a `request: Request` parameter.
- **Errors** (`core/errors.py`, see `docs/Sprint3-Format-erreurs.md`): every error response is `{"code", "message"}` (plus `fields` for 422). In routes, `raise ApiError("code")`, never `HTTPException`. Add new codes to the `ERRORS` catalogue (status + French message) and to the Sprint 3 table. Global handlers cover library 401/403/404/405, validation errors, 429 and 500.
- **Logs**: use `logging.getLogger(__name__)` (the `app` logger is configured in `main.py`, level `LOG_LEVEL`), not `print()`. Never log emails, passwords or tokens.
