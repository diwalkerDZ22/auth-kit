# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

`auth-kit` is a reusable authentication module **shipped as libraries**, extracted from the FakeJobApplicationRecognition project (history kept). It must stay project-agnostic: no business logic from a consuming project belongs here, and nothing may rely on global state or import-time side effects.

- `backend/src/auth_kit/`: Python package `auth-kit` (FastAPI). `backend/example/`: demo app showing how a project integrates it.
- `frontend/packages/auth-kit/`: npm package `@auth-kit/react` (TypeScript sources, three entry points). `frontend/apps/demo/`: demo app. npm workspaces rooted at `frontend/`.
- `docs/Bibliotheque.md`: library architecture and integration guide (read first). `docs/Sprint*.md`: design docs per feature (paths cited in Sprints 1-7 predate the package layout).

Code comments, log messages, docs and API error messages are in French. Keep that convention.

## Commands

Backend, from `backend/` (`pyproject.toml` sets pytest `pythonpath = ["src", "."]`; `alembic.ini` has `prepend_sys_path = src`):

```bash
python -m pip install -r requirements.txt          # pinned deps + the kit in editable mode (auth-kit command)
python -m pip install -r requirements-dev.txt      # + pytest, httpx2 (Starlette 1.x TestClient needs httpx2, not httpx)
python -m pytest
alembic upgrade head                               # kit migrations, branch "auth_kit"; DB from DATABASE_URL / .env / -x database_url=
auth-kit seed-roles | cleanup [--days 7] | test-email <to> [--purpose login] [--backend console] | migrations-path
python -m uvicorn --factory example.main:create_app --reload
python -m example.openapi ../frontend/packages/auth-kit/openapi.json   # after any API schema change
```

Frontend, from `frontend/`: `npm install`, `npm run dev` (demo on 5173, proxies `/api/*` to `http://127.0.0.1:8000/*`), `npm test` (Vitest + happy-dom + Testing Library, package only), `npm run lint` (oxlint), `npm run build` (package typecheck + demo `tsc -b && vite build`), `npm run gen:api` (regenerates `src/client/api.gen.ts` from `openapi.json` via `npx` with TypeScript 5, because openapi-typescript does not support the project's TypeScript 7). Keep test, lint and build warning-free (the demo main chunk must stay under Vite's 500 kB warning: kit pages are lazy-loaded).

**Contract**: `backend/tests/test_example.py::test_contrat_openapi_a_jour` fails when `frontend/packages/auth-kit/openapi.json` is stale. After changing a schema or route: dump the OpenAPI, run `npm run gen:api`, then fix the frontend types it breaks. Never hand-edit `api.gen.ts`; `client/types.ts` only aliases generated schemas.

## Backend architecture (`src/auth_kit/`)

- **Assembly** (`kit.py`): `AuthKit(settings, get_db, email, rate_limiter=None, breach_checker=None, templates=None, features=FEATURES, permissions=None, roles=None, errors=None)` builds a `KitContext` (`context.py`), the error catalogue, the FastAPI dependencies and the routers. `kit.install(app, auth_prefix="/auth", admin_prefix="/admin", error_scope="kit"|"app"|"none")`. Exposes `kit.current_user`, `kit.require_permission(code)`, `kit.rate_limit(limit)`, `kit.seed_roles(db)`, `kit.cleanup(db)`.
- **Layers**: `http/` (thin FastAPI layer: `routers/*` are `build_*_router(ctx, deps)` factories, `deps.py` builds dependencies bound to the kit, `schemas.py` is the OpenAPI source, `cookies.py`) → `services/` (use cases, **no FastAPI imports**, take `db` and `ctx` explicitly; they return `EmailMessage`s that routes send as `BackgroundTask`s, except the login email which is sent synchronously) → `ports.py` (Protocols `EmailSender`, `RateLimiter`, `BreachChecker`) / `models.py`. Implementations in `adapters/` (Resend, console, memory; `LimitsRateLimiter`, `NoRateLimiter`; `HibpBreachChecker`). Only adapters import third-party providers.
- **Config** (`config.py`): `AuthSettings` (pydantic-settings, `env_prefix="AUTH_"`, lowercase fields, no `.env` read unless `_env_file=` is passed). Infrastructure (DB URL, CORS, mail provider keys, Redis, logging) is **not** kit config: it belongs to the app (`example/main.py` `AppSettings`). Per-IP limits: `DEFAULT_RATE_LIMITS` merged with `settings.rate_limits`.
- **Features**: `register`, `password_reset`, `devices`, `admin` are optional; login, verify, refresh/logout, `/me`, password change and `GET /config` are always mounted. `/config` publishes features and password rules for the frontend; add new public rules there instead of duplicating them.
- **Auth dependencies** (`http/deps.py`): `token_payload` (HTTPBearer with `auto_error=False`, so a missing token is an `ApiError("not_authenticated")` in kit format even on project routes) → `current_user` (`sub` = **user id**, checks `ver` = `User.token_version` and that session `sid` is active) → `current_active_user` (rejects disabled / unverified) → `require_permission(code)`. `rate_limit(name, limit=None)` keys on `request.client.host`.
- **Sessions** (`services/sessions.py`, table `user_sessions`): one row per device; the refresh cookie holds an opaque random token, only its SHA-256 is stored; `refresh_session()` rotates it, accepts the previous token for `refresh_reuse_grace_seconds` (new access token, no new cookie) and revokes the session if it is reused later. `open_session()` is the single place sessions start. `accounts.revoke_all_sessions(user)` bumps `token_version` and revokes every session; `set_password()` calls it and also cancels pending login/reset links.
- **Email links** (`services/verification.py`, table `email_verifications`): purposes `signup` (24h), `login` (15 min, approve via `/verify` or `/login/deny`, page polls `/login/claim` within `login_claim_window_minutes`), `reset` (30 min, only via `/password/reset`). Links are `<frontend url>?token=...&type=<purpose>`; only hashes are stored; a new link invalidates older unused ones; `sent_recently()` is the single anti-spam check. Register returns the same response when the email exists (owner gets an "account exists" mail, max `account_exists_mail_limit`); only `username_taken` is revealed. Unknown usernames still run bcrypt (`burn_password_check`).
- **Emails** (`templates.py`): `EmailTemplates` dataclass (texts, brand colour) rendered by `render_link_email` / `render_account_exists_email` into `EmailMessage(to, subject, text, html, purpose)`. HTML is table-based with inline styles (mail clients).
- **Passwords** (`passwords.py`): `password_problem()` (static rules, used by Pydantic validators via `PydanticCustomError("kit_...")`) and `new_password_error(ctx, ...)` (static rules + `ctx.breach_checker`). Hashing: `bcrypt` library directly; `verify_password` returns False above 72 bytes.
- **Errors** (`errors.py`, see `docs/Sprint3-Format-erreurs.md`): `raise ApiError("code")` (never `HTTPException`); status and message are resolved by the kit's `ErrorCatalogue` when responding (unknown code → logged, 500 `internal_error`). Add kit codes to `DEFAULT_ERRORS` and to the Sprint 3 table. `install_error_handlers(app, catalogue, prefixes)` scopes the generic 404/422/500 format to the kit's prefixes unless `error_scope="app"`.
- **RBAC**: `User.role_id` → `Role` ↔ `Permission` (`role_permissions`). Defaults in `context.py` (`user`, `admin` with `ADMIN_PERMISSION = "users:manage"`); projects pass their own `roles`/`permissions` and call `kit.seed_roles(db)` (idempotent, resyncs listed roles' permissions).
- **DB**: `db.py` only offers helpers (`create_engine_from_url(url, sslmode="require")`, `normalize_database_url`, `session_dependency`). `models.Base` can be reused by projects. Use `sqltypes.UTCDateTime` for new datetime columns.
- **Migrations** (`migrations/`, branch label `auth_kit` on the root revision; revision ids unchanged so existing DBs such as Supabase stay compatible) must run on an empty DB, PostgreSQL and SQLite: `op.batch_alter_table` for alter/drop/constraints, PostgreSQL-only SQL guarded by `op.get_bind().dialect.name` (e.g. enable RLS on new tables). Check drift with `alembic check`.
- **Logs**: `logging.getLogger(__name__)` (loggers `auth_kit.*`); the kit never configures handlers. Never log emails, passwords or tokens (only exception: `ConsoleEmailSender`, dev only).

Tests: `tests/conftest.py` builds a test app with its own `AuthKit` (temp SQLite, `MemoryEmailSender` outbox of `EmailMessage`, `LimitsRateLimiter(enabled=False)` toggled per test, roles seeded with `kit.seed_roles`). Helpers: `make_user`, `login` (full email flow), `link_token`, `bearer`. Build other kits with different options in a test rather than mutating the shared one (see `test_library.py`).

## Frontend architecture (`packages/auth-kit/src/`)

- **Entry points** (`package.json` `exports`, TypeScript sources consumed by the app's bundler): `./client` (no React), `./react` (state, guards, headless hooks), `./ui` (pages, components, theme) and `./ui/styles.css`. Lower layers never import higher ones (`client` ← `react` ← `ui`).
- **Client** (`client/client.ts`): `createAuthClient({ baseUrl, authPrefix, adminPrefix, fetch, channelName, lockName })` returns an instance; no module-level state. Access token in memory only (never localStorage/sessionStorage); refresh token is the httpOnly cookie. `refreshSession()` is single-flight per instance and across tabs (`navigator.locks`); `send()` replays once after a 401 `invalid_token`; refresh scheduled before expiry; logout broadcast on a `BroadcastChannel`. `client.request()` also serves the project's own API routes.
- **React** (`react/`): `<AuthProvider client paths>` restores the session with `/refresh`, loads `/config` and `/me` with TanStack Query (keys in `context.ts`). `useAuth()` gives `status`, `user`, `hasPermission`, `hasFeature`, `config`, `client`, `paths`. Guards `RequireAuth`, `RequirePermission`, `GuestOnly` use configurable `paths` (`paths.ts`, `DEFAULT_PATHS`). Hooks in `hooks.ts` hold all page logic (`useLoginFlow` polling, `useDevices`, `useAdminUsers`...).
- **UI** (`ui/`): `createAuthRoutes(paths)` (all pages lazy-loaded), pages in `pages/`, components in `components.tsx` (`ak-*` classes from `styles.css`, no Tailwind), texts in `messages.ts` (`FR`, partial overrides through `<AuthUIProvider messages brand>`), form schemas built from `/config` rules (`schemas.ts`, `useSchemas()`), link tokens read through the router (`useLinkToken`, works with any router). Show backend errors with `applyApiError()`; never duplicate backend messages.
- **Theme**: CSS variables `--ak-*` on `:root`, dark values under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])` and again under `:root[data-theme="dark"]` (keep both blocks in sync). `theme.ts` stores the choice (`auth-kit-theme` in localStorage, wrapped in try/catch) and sets `data-theme`; `THEME_INIT_SCRIPT` avoids a flash. Respect `prefers-reduced-motion`.
- **Lint rule** `react/only-export-components`: files exporting components export only components; put hooks, contexts and helpers in `.ts` files (e.g. `ui/context.ts`, `ui/theme.ts`, `ui/strength.ts`, `ui/devices.ts`). Use `useWatch` rather than `form.watch` (React Compiler compatibility).
- `tsconfig` uses `strict`, `verbatimModuleSyntax` and `erasableSyntaxOnly`: `import type` for types, no enums, no constructor parameter properties.
