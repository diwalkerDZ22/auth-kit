# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

`auth-kit` is a reusable authentication module, extracted from the FakeJobApplicationRecognition project (history kept). It must stay project-agnostic: no business logic from a consuming project belongs here.

- `backend/`: FastAPI authentication/authorization service.
- `frontend/`: React + TypeScript (Vite) app, planned.
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

There is no test suite and no linter config.

## Backend architecture

- **Config** (`app/core/config.py`): a pydantic-settings `Settings` singleton loaded from `.env`. `DATABASE_URL` may be SQLite or PostgreSQL. `app/db/base.py` rewrites `postgresql://` to `postgresql+psycopg://` and forces `sslmode=require`. `alembic/env.py` takes the DB URL from these settings, not from `alembic.ini`.
- **Routers** (`app/main.py`): `api/auth.py` (logout, `/me`, auth dependencies) and `api/authentification/{login,register}.py` are mounted under `/auth`. `admin.py` is mounted at the root. `jobs.py` is a leftover stub from FakeJob, to be removed.
- **Auth dependencies** (`api/auth.py`): `get_current_user` decodes the bearer JWT (`sub` = username) → `get_current_active_user` rejects disabled or unverified accounts → `require_permission("code")` is a dependency factory that checks the user's role permissions. Protect new routes with `Depends(require_permission(...))`.
- **RBAC** (`db/models.py`): `User.role_id` points to `Role`, which has many-to-many `Permission` rows via `role_permissions`. Permission codes are strings like `users:manage`. Roles and permissions are declared in `scripts/seed_roles.py`, which is idempotent and resyncs each role's permissions. Add new permissions there.
- **Tokens** (`core/security.py`, `core/tokens.py`): access and refresh tokens are both HS256 JWTs signed with the same secret, told apart by `type: "access"` / `type: "refresh"`; `get_current_user` rejects anything but `access`. Only the latest refresh token is stored on `User.refresh_token`, and logout clears it. `issue_tokens()` is the single place where tokens are issued.
- **Email verification, two purposes** (`core/verification.py`, table `email_verifications`, sent through Resend in `core/email.py` as a `BackgroundTask`):
  - `signup`: `/auth/register` creates the user with `is_verified=False` and emails a link (24h). `POST /auth/verify` sets `is_verified`. `/auth/resend-verification` gives the same response whether or not the account exists.
  - `login`: when the password is correct, `/auth/token` does **not** return JWTs. It emails a link (15 min, max 1 per minute) and returns 202 with an `attempt_id`. Clicking the link calls `POST /auth/verify`, which only sets `approved_at`. The original page polls `POST /auth/login/claim` with `attempt_id` and gets the tokens within 2 minutes of approval (`claimed_at`).
  - Only SHA-256 hashes of the link token and of the `attempt_id` are stored. Creating a new link invalidates earlier unused links of the same user and purpose by setting `used_at`.
  - With `LOGIN_EMAIL_REQUIRED=false` (dev only), `/auth/token` returns tokens directly, which makes Swagger testing possible.
- The frontend is expected at `http://localhost:5173` (`CORS_ORIGINS` and `FRONTEND_VERIFY_URL` in settings). `GET /auth/verify` serves a minimal HTML confirm page for testing without the frontend.
- `slowapi` (`core/limiter.py`, per-IP, in-memory) limits every public `/auth/*` POST route with `@limiter.limit(...)`. Rate-limited routes need a `request: Request` parameter.
- **Errors** (`core/errors.py`, see `docs/Sprint3-Format-erreurs.md`): every error response is `{"code", "message"}` (plus `fields` for 422). In routes, `raise ApiError("code")`, never `HTTPException`. Add new codes to the `ERRORS` catalogue (status + French message) and to the Sprint 3 table. Global handlers cover library 401/403/404/405, validation errors, 429 and 500.
- **Logs**: use `logging.getLogger(__name__)` (the `app` logger is configured in `main.py`, level `LOG_LEVEL`), not `print()`. Never log emails, passwords or tokens.
