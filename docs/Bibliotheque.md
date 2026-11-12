# Sprint 8 : auth-kit en bibliothèque

auth-kit n'est plus un dossier à copier : c'est un package Python (`auth-kit`, import `auth_kit`) et un package npm (`@auth-kit/react`). Le projet qui les utilise garde la main sur son infrastructure (base, CORS, mails, Redis) et branche le kit avec quelques lignes.

## Backend

### Installation

```bash
pip install "auth-kit[resend,postgres] @ git+https://github.com/<compte>/auth-kit.git#subdirectory=backend"
```

Extras : `resend` (envoi Resend), `postgres` (psycopg), `redis` (rate-limit partagé), `dotenv` (lecture de `.env` par la CLI et les migrations).

### Intégration minimale

```python
from fastapi import Depends, FastAPI
from sqlalchemy.orm import sessionmaker

from auth_kit import AuthKit, AuthSettings, CSRF_HEADER
from auth_kit.adapters import HibpBreachChecker, LimitsRateLimiter, ResendEmailSender
from auth_kit.db import create_engine_from_url, session_dependency
from auth_kit.models import User

engine = create_engine_from_url(DATABASE_URL)            # sslmode="require" par défaut
get_db = session_dependency(sessionmaker(bind=engine))   # ou la dépendance get_db existante du projet

kit = AuthKit(
    settings=AuthSettings(),                             # variables AUTH_* (AUTH_SECRET_KEY obligatoire)
    get_db=get_db,
    email=ResendEmailSender(RESEND_API_KEY, "Mon app <no-reply@mon-app.fr>"),
    rate_limiter=LimitsRateLimiter("redis://localhost:6379"),   # "memory://" si un seul process
    breach_checker=HibpBreachChecker(),                  # facultatif
)

app = FastAPI()
kit.install(app)   # /auth/* et /admin/*

@app.get("/jobs")
def jobs(user: User = Depends(kit.current_user)): ...

@app.post("/jobs/{id}/classify", dependencies=[Depends(kit.require_permission("jobs:classify"))])
def classify(id: int): ...
```

`example/main.py` est une intégration complète (CORS, logs, choix des adaptateurs selon l'environnement).

### Ce que le kit ne fait plus tout seul

| Avant (copie du dossier `app/`) | Maintenant |
|----------------------------------|------------|
| `settings = Settings()` à l'import, lit le `.env` du dossier courant | `AuthSettings()` créé par le projet ; préfixe `AUTH_` pour ne pas entrer en collision avec ses variables |
| `engine` créé à l'import, base propre au kit | le projet fournit `get_db` (sa propre session) |
| Resend importé en dur | interface `EmailSender` : `ResendEmailSender`, `ConsoleEmailSender`, `MemoryEmailSender`, ou la vôtre |
| slowapi, limiter global | interface `RateLimiter` : `LimitsRateLimiter(storage_uri)`, `NoRateLimiter` |
| HIBP appelé en dur | interface `BreachChecker` : `HibpBreachChecker`, ou aucune |
| `main.py` configure les logs et des gestionnaires d'erreurs pour toute l'app | le kit ne touche pas aux logs ; format d'erreur limité à ses routes (voir plus bas) |
| `sub` du JWT = username | `sub` = id utilisateur |

Aucun état global : deux `AuthKit` peuvent cohabiter (tests, multi-tenant).

### Architecture

```
src/auth_kit/
  kit.py          AuthKit : assemble tout, monte les routes
  config.py       AuthSettings (AUTH_*), DEFAULT_RATE_LIMITS
  context.py      KitContext (ce que reçoivent les services), rôles par défaut
  ports.py        EmailSender, RateLimiter, BreachChecker (Protocols)
  adapters/       Resend, console, mémoire ; limits (mémoire / Redis) ; HIBP
  services/       cas d'usage sans FastAPI : accounts, login, sessions, recovery,
                  verification, admin, roles, maintenance
  http/           couche FastAPI mince : routers/, deps.py, schemas.py, cookies.py
  models.py       tables (Base réutilisable par le projet)
  templates.py    textes et HTML des mails (remplaçables)
  errors.py       ApiError, catalogue, gestionnaires
  migrations/     branche Alembic "auth_kit"
  cli.py          commande auth-kit
```

Dépendances : `http → services → ports / models`. Les services n'importent jamais FastAPI : ils servent aussi depuis une CLI ou une tâche de fond.

### Fonctionnalités optionnelles

```python
AuthKit(..., features={"password_reset", "devices"})   # pas d'inscription publique, pas d'admin
```

| Fonctionnalité | Routes |
|----------------|--------|
| toujours | `/token`, `/login/claim`, `/login/deny`, `/verify`, `/refresh`, `/logout`, `/me`, `/password/change`, `/config` |
| `register` | `/register`, `/resend-verification` |
| `password_reset` | `/password/forgot`, `/password/reset` |
| `devices` | `/sessions` (GET, DELETE), `/sessions/{id}` (DELETE) |
| `admin` | `/admin/users`, `/admin/users/{id}`, `/admin/roles` |

`GET /auth/config` publie les fonctionnalités actives et les règles de mot de passe : le frontend s'y adapte (liens masqués, règles des formulaires).

### Personnaliser

```python
from dataclasses import replace
from auth_kit import EmailTemplates, LinkEmail, RoleSpec

kit = AuthKit(
    ...,
    # Rôles et permissions du projet (kit.seed_roles(db) les crée / synchronise)
    permissions={"users:manage": "Admin", "jobs:classify": "Classer les offres"},
    roles={
        "user": RoleSpec("Utilisateur"),
        "recruteur": RoleSpec("Recruteur", ("jobs:classify",)),
        "admin": RoleSpec("Administrateur", ("users:manage", "jobs:classify")),
    },
    # Codes d'erreur du projet, ou messages du kit traduits
    errors={"job_not_found": (404, "Offre introuvable."), "invalid_credentials": (401, "Wrong credentials.")},
    # Mails : couleur, textes
    templates=replace(EmailTemplates(), brand_color="#0f766e"),
)
```

- `raise ApiError("job_not_found")` dans les routes du projet : même format `{code, message}` que le kit.
- `Depends(kit.rate_limit("20/minute"))` : limite par IP pour une route du projet.
- Limites des routes du kit : `AUTH_RATE_LIMITS='{"login": "20/15minutes"}'`.
- Préfixes : `kit.install(app, auth_prefix="/api/compte", admin_prefix="/api/gestion")`.

### Format d'erreur

`kit.install(app, error_scope=...)` :

- `"kit"` (défaut) : 404 / 422 / 500 au format du kit sur ses routes seulement ; les routes du projet gardent le format FastAPI.
- `"app"` : format du kit partout.
- `"none"` : aucun gestionnaire ; le projet appelle `install_error_handlers(app, kit.errors, prefixes)` lui-même.

`ApiError` est toujours rendue au format du kit, et les dépendances du kit (`kit.current_user`...) aussi, même sur une route du projet (`not_authenticated`, `invalid_token`...) : le client frontend s'y fie pour rafraîchir la session.

### Base de données et migrations

Les modèles déclarent leur propre `Base`. Deux façons d'y relier les tables du projet :

```python
from auth_kit.models import Base, User      # 1. une seule metadata (recommandé)
class Job(Base):
    __tablename__ = "jobs"
    owner_id = Column(ForeignKey("users.id"))

owner_id = Column(ForeignKey(User.id))      # 2. metadata du projet, clé étrangère par colonne
```

Les migrations du kit forment la branche Alembic `auth_kit` (mêmes identifiants de révision qu'avant : une base déjà migrée, comme celle de Supabase, est compatible).

- **Base dédiée ou démo** : `cd backend && alembic upgrade head`.
- **Projet avec ses propres migrations** : ajouter le dossier du kit à `version_locations` dans son `alembic.ini` (`auth-kit migrations-path` l'affiche), mettre `auth_kit.models.Base.metadata` dans `target_metadata` de son `env.py`, puis :

  ```bash
  alembic upgrade heads              # toutes les branches (kit + projet)
  ```

  Une migration du projet qui dépend des tables du kit déclare `depends_on = "auth_kit@head"`.

### Commande `auth-kit`

```bash
auth-kit seed-roles                 # rôles par défaut (rôles du projet : kit.seed_roles(db))
auth-kit cleanup --days 7           # liens et sessions périmés : à planifier
auth-kit test-email moi@exemple.fr --purpose login --backend console
auth-kit migrations-path
```

Base : `--database-url` ou `DATABASE_URL` (variable ou `.env`), `DATABASE_SSLMODE`.

## Frontend

### Installation

`@auth-kit/react` se consomme depuis le dépôt (sources TypeScript, compilées par le bundler du projet, Vite par exemple) :

```bash
npm install "file:../auth-kit/frontend/packages/auth-kit"   # ou un workspace npm
```

Peer dependencies : `react`, `react-dom`, `@tanstack/react-query`, `react-router` ; `react-hook-form`, `zod`, `@hookform/resolvers` pour les pages (`/ui`).

### Trois points d'entrée

| Import | Contenu | Pour qui |
|--------|---------|----------|
| `@auth-kit/react/client` | `createAuthClient()`, `ApiError`, types | n'importe quel framework, ou sans React |
| `@auth-kit/react/react` | `AuthProvider`, `useAuth`, gardes, hooks (`useLoginFlow`, `useDevices`, `useAdminUsers`...) | un projet avec son propre design system |
| `@auth-kit/react/ui` (+ `ui/styles.css`) | pages prêtes, `createAuthRoutes()`, composants, `ThemeToggle` | mise en place rapide |

```tsx
import { createAuthClient } from '@auth-kit/react/client'
import { AuthProvider } from '@auth-kit/react/react'
import { AuthUIProvider, createAuthRoutes } from '@auth-kit/react/ui'
import '@auth-kit/react/ui/styles.css'

const client = createAuthClient({ baseUrl: '/api' })   // authPrefix / adminPrefix si kit.install(...) les change
const paths = { login: '/connexion' }                  // facultatif : chemins des pages

<QueryClientProvider client={queryClient}>
  <AuthProvider client={client} paths={paths}>
    <AuthUIProvider brand={{ name: 'Mon app' }} messages={{ login: { title: 'Bienvenue' } }}>
      <RouterProvider router={createBrowserRouter([{ element: <Layout />, children: [...createAuthRoutes(paths), ...mesRoutes] }])} />
    </AuthUIProvider>
  </AuthProvider>
</QueryClientProvider>
```

- `client.request('/jobs')` : appels vers les routes métier du projet, avec token et refresh gérés.
- Les chemins `verifyEmail` et `resetPassword` doivent correspondre à `AUTH_FRONTEND_VERIFY_URL` et `AUTH_FRONTEND_RESET_URL`.
- Toutes les pages sont chargées à la demande (`createAuthRoutes`) : les formulaires ne pèsent pas sur le chargement initial.

### Thème et style

- Clair, sombre ou système : `<ThemeToggle />` (ou `useTheme()`), choix mémorisé. Script anti-flash : `THEME_INIT_SCRIPT` dans `<head>` (voir `apps/demo/index.html`).
- Mode sombre piloté par `<html data-theme="dark|light">` ; sans attribut, suit le système.
- Charte : redéfinir les variables `--ak-*` (couleurs, rayons, police, dégradé) dans le CSS du projet. Les classes sont préfixées `ak-` : aucun conflit, pas besoin de Tailwind.
- Composants réutilisables dans les pages du projet : `Section`, `Button`, `Field`, `Alert`, `Badge`, `Avatar`, `Icon`...

### Contrat avec le backend

Les types TypeScript sont générés depuis l'OpenAPI du backend, pas écrits à la main :

```bash
cd backend && python -m example.openapi ../frontend/packages/auth-kit/openapi.json
cd ../frontend && npm run gen:api
```

`tests/test_example.py::test_contrat_openapi_a_jour` échoue si `openapi.json` n'est plus à jour : un changement de schéma côté backend ne peut pas passer inaperçu côté frontend.

## Migration d'un projet existant (FakeJobApplicationRecognition)

1. `.env` : préfixer les réglages du kit par `AUTH_` (`SECRET_KEY` → `AUTH_SECRET_KEY`, `LOGIN_EMAIL_REQUIRED` → `AUTH_LOGIN_EMAIL_REQUIRED`, `COOKIE_SECURE` → `AUTH_COOKIE_SECURE`, `FRONTEND_*_URL` → `AUTH_FRONTEND_*_URL`, `VERIFY_TEST_PAGE` → `AUTH_VERIFY_TEST_PAGE`...). `DATABASE_URL`, `RESEND_API_KEY`, `MAIL_FROM`, `CORS_ORIGINS` restent des réglages du projet.
2. Remplacer `require_permission` / `get_current_active_user` importés de `app.api.auth` (ou `app.api.deps`) par `kit.require_permission` et `kit.current_user`.
3. Remplacer les rôles de `scripts/seed_roles.py` par `AuthKit(roles=..., permissions=...)` + `kit.seed_roles(db)`.
4. Migrations : ajouter `version_locations` (voir plus haut). La base Supabase est déjà à la révision `7c4e1a9b2f30` ou avant : `alembic upgrade heads` suffit.
5. Frontend : remplacer le dossier `src/auth/` copié par `@auth-kit/react`, passer le client à `<AuthProvider client={...}>` et utiliser `createAuthRoutes()`.
6. Les access tokens émis avant la mise à jour ont `sub` = username : ils sont refusés, chacun se reconnecte une fois.

## Tests

- Backend (`cd backend && python -m pytest`) : 66 tests. `tests/conftest.py` monte le kit dans une application de test comme le ferait un projet ; `tests/test_library.py` couvre les fonctionnalités optionnelles, les préfixes, la portée des erreurs, les codes et rôles du projet, les mails personnalisés, `sub` = id, deux kits indépendants ; `tests/test_example.py` l'application de démo, le CORS et le contrat OpenAPI.
- Frontend (`cd frontend && npm test`) : 38 tests. Client (instances indépendantes, préfixes, refresh partagé, rejeu), gardes avec chemins personnalisés, pages selon les fonctionnalités, textes et marque personnalisés, thème, règles venues de `/auth/config`.
