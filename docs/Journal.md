# Journal d’auth-kit

Ce qui a été fait, dans l’ordre, avec ce que git ne garde pas : opérations sur la base de données, environnement local, points ouverts. Le détail des choix est dans chaque `SprintN-*.md`.

---

## 2026-11-11

### Dans FakeJobApplicationRecognition (avant l’extraction)

Branche `feat/verification-mail` :

| Commit | Contenu |
|--------|---------|
| `db36336` | Sécurité : refresh token refusé comme access token (`type`), rate-limit slowapi, emails en minuscules, expiration par défaut 30 min, `CORS_ORIGINS` |
| `cd8a468` | Sprint 3 : format d’erreur `{"code", "message"}`, catalogue `ERRORS`, logs `logging` sans email ; bilan du Sprint 2 |

Branche `feat/classification-contract` (métier, mis de côté) :

| Commit | Contenu |
|--------|---------|
| `563b8a1` | Sprint 4 : contrat de `/jobs/classify` (`JobOfferIn` / `ClassificationOut`) avec une heuristique provisoire `heuristique-v0` |

### Extraction d’auth-kit

- Dépôt créé à partir de `auth_app/` de FakeJob avec `git subtree split` : les 20 commits d’origine sont conservés.
- Structure : `backend/` (code), `docs/` (Sprints 1 à 3), `README.md`, `CLAUDE.md`, `.gitignore` (`.env`, `*.db`, `node_modules/`).
- Publié en privé : `https://github.com/diwalkerDZ22/auth-kit` (branche `main`).

### Sprint 5 : authentification complète (`3f74ff7`)

Mot de passe oublié, profil, changement de mot de passe, administration, règles de mot de passe et de username, révocation immédiate (`token_version`), `jti` dans les JWT, mail de login synchrone (503 `email_unavailable`), migrations rejouables sur une base vide (PostgreSQL et SQLite), `UTCDateTime`, nettoyage des restes de FakeJob, 19 tests pytest. Voir `Sprint5-Auth-complete.md`.

### Sprint 6 : frontend React

- Backend : refresh token en cookie httpOnly (`core/cookies.py`), `AccessToken` dans les corps de réponse, header CSRF sur `/auth/refresh` et `/auth/logout`, `EMAIL_BACKEND=console` pour le dev. 21 tests pytest.
- Frontend `frontend/` : Vite, React 19, TypeScript, Tailwind 4, React Router 8, TanStack Query, React Hook Form + Zod 4. Module réutilisable `src/auth/`, démo `src/app/`.
- Voir `Sprint6-Frontend.md`.

---

## Opérations sur la base Supabase (hors git)

La base PostgreSQL (Supabase) est **partagée** avec FakeJob : même `DATABASE_URL`, le `.env` de `backend/` est une copie de celui de `FakeJobApplicationRecognition/auth_app/`. FakeJob sera plus tard écrasé par auth-kit, la base peut donc évoluer librement.

| Opération | Effet |
|-----------|-------|
| `alembic upgrade head` | `15113d760132` → `d6a33616f033` : colonne `users.token_version` (entier, défaut 0) ; contrainte `ck_email_verifications_purpose` étendue à `reset` |
| `python scripts/seed_roles.py` | `user` : aucune permission ; `admin` : `users:manage`. La permission `jobs:classify` reste en base mais n’est plus liée à aucun rôle |
| Compte `usertest` (id 12, dhiawalker@gmail.com) | Passé en rôle `admin`, `is_verified = true`, `token_version` incrémenté. C’est le compte admin de test : son adresse est la seule à laquelle Resend envoie en dev |
| Compte `dhia` (id 11, dhia@gmail.com) | Inchangé : déjà `admin`, mais son adresse ne reçoit pas les mails Resend en dev (connexion impossible avec `LOGIN_EMAIL_REQUIRED=true`) |

Conséquences :

- Les tokens émis avant `d6a33616f033` n’ont pas de `ver` : ils sont refusés, il faut se reconnecter.
- Alembic de FakeJob ne connaît pas `d6a33616f033` : `alembic upgrade` y échoue (« Can’t locate revision ») tant que FakeJob n’est pas remplacé par auth-kit.
- Le code actuel de FakeJob ne vérifie ni `ver` ni `jti` : ses tokens ne sont pas révoqués par les opérations d’auth-kit.

---

## Environnement local

- `backend/.env` copié depuis FakeJob ; ajout de `COOKIE_SECURE=false` (dev en HTTP). Non versionné.
- `pytest` et `httpx2` installés dans le Python utilisateur (`backend/requirements-dev.txt`).
- GitHub CLI (`gh`) non installé : le dépôt GitHub a été créé à la main.

### Lancer le kit en local sur Supabase

```bash
# backend (depuis backend/)
LOGIN_EMAIL_REQUIRED=true EMAIL_BACKEND=resend COOKIE_SECURE=false python -m uvicorn app.main:app --port 8000
# frontend (depuis frontend/)
npm run dev        # http://localhost:5173
```

Sans boîte mail : `EMAIL_BACKEND=console`, les liens apparaissent dans les logs du backend (lignes `[EMAIL_BACKEND=console]`).

Sans toucher à Supabase : ajouter `DATABASE_URL=sqlite:///./e2e.db`, puis `alembic upgrade head` et `python scripts/seed_roles.py`.

---

## Vérifications faites

| Vérification | Résultat |
|--------------|----------|
| `python -m pytest` (backend) | 21 tests passés |
| `npm run build` / `npm run lint` (frontend) | sans erreur ni avertissement |
| Parcours complet à travers le proxy Vite, base SQLite de test, `EMAIL_BACKEND=console` (17 étapes : inscription, vérification, connexion par email, cookie, refresh, CSRF, profil, mot de passe, logout, reset) | OK |
| Migrations sur une base SQLite vide, aller-retour de `d6a33616f033` | OK |
| Migration `d6a33616f033` sur Supabase | OK (colonne et contrainte vérifiées) |
| Affichage des pages dans un navigateur | **À faire** (extension Chrome non connectée lors du sprint) ; test manuel en cours sur Supabase avec `usertest` |

---

## Points ouverts

- Vérifier l’affichage de toutes les pages dans un navigateur.
- Resend en dev n’envoie qu’à l’adresse du compte Resend : vérifier un domaine et le mettre dans `MAIL_FROM` pour tester d’autres adresses (et pour la prod).
- Production : reverse proxy qui sert le frontend et relaie `/api` vers le backend (même origine), `COOKIE_SECURE=true`, `EMAIL_BACKEND=resend`, `LOGIN_EMAIL_REQUIRED=true`.
- Rate-limit en mémoire : à passer sur Redis si plusieurs instances.
- Inscription et renvoi de mail répondent « envoyé » même si Resend échoue (envoi en tâche de fond) ; seul le mail de login renvoie 503.
- `last_admin` est inatteignable par l’API tant que `cannot_modify_self` existe (garde-fou).
- Changement d’email ou de username : hors périmètre (sprint dédié).
- Remplacer `auth_app/` de FakeJob par auth-kit, puis rebrancher le métier (`feat/classification-contract`, permission `jobs:classify` à ajouter dans `seed_roles.py`).
