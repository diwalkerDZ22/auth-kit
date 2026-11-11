# Sprint5: Authentification complète

## Contexte

`auth-kit` a été extrait de FakeJobApplicationRecognition pour servir de module d’authentification réutilisable. Le backend couvre déjà l’inscription vérifiée, la connexion par lien email, les tokens, les rôles et un format d’erreur unique (Sprints 1 à 3).

Pour qu’un frontend puisse proposer une authentification **complète**, il manque :

1. Le **mot de passe oublié**.
2. La gestion du **profil** et le **changement de mot de passe**.
3. L’**administration** des utilisateurs (prévue au Sprint 1, jamais faite).
4. Des **règles** sur le mot de passe et le username.
5. La **révocation immédiate** des sessions (aujourd’hui un access token reste valable jusqu’à son expiration, même après logout ou désactivation).

Et il reste des traces du projet d’origine à retirer.

---

## Choix retenus

| Choix | Raison |
|--------|--------|
| Reset par lien email, nouveau `purpose = "reset"` (30 min) | Réutilise `email_verifications` : hash, usage unique, rotation |
| `/auth/verify` n’accepte que `signup` et `login` | Un lien de reset ne doit pas pouvoir approuver une connexion |
| Reset réussi → `is_verified = True` | Cliquer le lien prouve la possession de l’email |
| `token_version` sur `User`, copié dans le JWT (`ver`) | Révocation immédiate : logout, changement / reset de mot de passe, désactivation, changement de rôle incrémentent la version |
| Changement de mot de passe → nouveaux tokens pour la session courante | Les autres sessions sont coupées, pas celle de l’utilisateur |
| Règles de mot de passe : 8 à 72 octets, différent du username / email, hors liste des mots de passe courants | Recommandations NIST (longueur plutôt que composition) ; 72 octets = limite de bcrypt |
| Username : 3 à 30 caractères, `a-z A-Z 0-9 _ . -` | Utilisable dans une URL et un log sans ambiguïté |
| Admin : pas d’auto-modification, pas de retrait du dernier admin | Éviter de se bloquer hors de l’application |
| Rôles du kit : `user` (aucune permission) et `admin` (`users:manage`) | Le projet qui utilise le kit ajoute ses propres permissions dans `seed_roles.py` |
| Mail de login envoyé de façon synchrone, 503 si Resend échoue | Reste du Sprint 2 : ne pas répondre « mail envoyé » quand il ne l’est pas |

---

## Nettoyage du projet d’origine

- Supprimer `app/api/jobs.py` et son router.
- `seed_roles.py` : retirer `jobs:classify` ; réutiliser l’engine de `app/db/base.py` (driver et SSL cohérents avec l’app).
- Titre de l’app (`FastAPI(title=...)`) et `MAIL_FROM_NAME` : venir d’un réglage `APP_NAME` (défaut `auth-kit`).
- SQLite : rendre les comparaisons de dates robustes (SQLite renvoie des dates sans fuseau). Reste du Sprint 2.

---

## Routes

### Mot de passe oublié

| Méthode | Path | Auth | Comportement |
|---------|------|------|----------------|
| POST | `/auth/password/forgot` | public | `{ "email" }` → mail avec lien `FRONTEND_RESET_URL?token=...` si le compte existe. **Toujours 200** générique. Max 1 mail / 2 min / compte |
| POST | `/auth/password/reset` | public | `{ "token", "new_password" }` → nouveau mot de passe, lien consommé, `token_version + 1`, refresh token effacé, `is_verified = True`. Pas de JWT : l’utilisateur se reconnecte |

### Profil

| Méthode | Path | Auth | Comportement |
|---------|------|------|----------------|
| PATCH | `/auth/me` | Bearer | `{ "full_name" }` → profil mis à jour (`UserMe`) |
| POST | `/auth/password/change` | Bearer | `{ "current_password", "new_password" }` → `token_version + 1`, renvoie un nouveau `TokenPair` |

Changer l’email ou le username est hors périmètre (demande une re-vérification ; sprint dédié si besoin).

### Administration (permission `users:manage`)

| Méthode | Path | Comportement |
|---------|------|----------------|
| GET | `/admin/users?search=&limit=&offset=` | Liste paginée (`items`, `total`), recherche sur username / email |
| GET | `/admin/users/{id}` | Détail d’un utilisateur |
| PATCH | `/admin/users/{id}` | `{ "role"?, "disabled"? }` → désactivation ou changement de rôle, `token_version + 1` |
| GET | `/admin/roles` | Rôles et leurs permissions |

### Révocation

- `POST /auth/logout` : efface le refresh token **et** incrémente `token_version`.
- `get_current_user` refuse un access token dont `ver` ≠ `user.token_version` (`invalid_token`).
- `/auth/refresh` vérifie aussi `ver`.

---

## Nouveaux codes d’erreur

| Code | HTTP | Quand |
|------|------|-------|
| `invalid_current_password` | 400 | Changement de mot de passe : mot de passe actuel faux |
| `user_not_found` | 404 | Admin : utilisateur inconnu |
| `role_not_found` | 400 | Admin : rôle inconnu |
| `cannot_modify_self` | 400 | Admin : modifier son propre compte |
| `last_admin` | 409 | Admin : retirer ou désactiver le dernier admin actif |
| `email_unavailable` | 503 | Envoi du mail de login impossible |

Mot de passe trop court, trop courant ou identique au username : `validation_error` (422) avec le message dans `fields.password` (ou `fields.new_password`).

---

## Modèle de données

- `users.token_version` : `Integer`, `NOT NULL`, défaut 0.
- `email_verifications.purpose` : contrainte étendue à `'signup', 'login', 'reset'`.
- Migration Alembic pour les deux.
- Réglages : `APP_NAME`, `FRONTEND_RESET_URL` (défaut `http://localhost:5173/reset-password`), `RESET_TOKEN_EXPIRE_MINUTES` (30).

---

## Ordre de mise en œuvre

1. Nettoyage (jobs, seed, `APP_NAME`, dates SQLite)
2. Migration `token_version` + `purpose = reset`
3. Révocation par `token_version` (JWT, `get_current_user`, refresh, logout)
4. Règles de mot de passe / username (schémas)
5. Mot de passe oublié (forgot + reset, mail `reset`)
6. Profil (`PATCH /auth/me`, `password/change`)
7. Administration
8. Mail de login synchrone + `email_unavailable`
9. Tests

---

## Tests

- Logout → l’ancien access token est refusé (`invalid_token`)
- Forgot email inconnu → 200 générique, aucun mail
- Reset avec lien valide → login possible avec le nouveau mot de passe, ancien refusé, anciens tokens refusés
- Lien de reset utilisé sur `/auth/verify` → `invalid_link`
- Reset lien expiré / déjà utilisé → `invalid_link`
- Password change mauvais mot de passe actuel → `invalid_current_password` ; succès → nouveaux tokens valables, anciens refusés
- Mot de passe `password123` ou de 5 caractères → 422 avec `fields.password`
- Username `a b` → 422 avec `fields.username`
- Admin sans `users:manage` → 403 ; liste paginée et recherche
- Admin se désactive lui-même → `cannot_modify_self` ; dernier admin → `last_admin`
- Désactivation d’un user → ses tokens sont refusés immédiatement
- Resend en panne au login → 503 `email_unavailable`, pas d’`attempt_id`

---

## Critères de done

- [x] Plus aucune trace métier de FakeJob dans le backend
- [x] Migration `token_version` + `reset`
- [x] Révocation immédiate (logout, mot de passe, désactivation, rôle)
- [x] Règles de mot de passe et de username
- [x] Mot de passe oublié de bout en bout
- [x] Profil et changement de mot de passe
- [x] Routes d’administration avec garde-fous
- [x] Mail de login synchrone, 503 si échec
- [x] Nouveaux codes dans `ERRORS` et dans le catalogue du Sprint 3
- [x] Tests ci-dessus passés

---

## Bilan (2026-11-11)

19 tests pytest (`backend/tests/`) couvrent les cas listés plus haut.

Ajouts par rapport au plan :

| Ajout | Raison |
|-------|--------|
| `jti` aléatoire dans chaque JWT | Deux tokens émis dans la même seconde étaient identiques : la rotation du refresh token ne servait à rien |
| Lien de login **supprimé** (pas consommé) si l'envoi échoue | Sinon l'anti-spam (1 mail / min) bloquait le nouvel essai |
| `SECRET_KEY` : 32 caractères minimum | Une clé vide était acceptée |
| Migrations rejouables sur une base vide (PostgreSQL et SQLite) | La table `users` n'était créée par aucune migration ; RLS Supabase seulement sur PostgreSQL |
| Type `UTCDateTime` | Dates toujours avec fuseau, y compris sous SQLite |

À savoir :

- `last_admin` ne peut pas être atteint par l'API tant que `cannot_modify_self` existe (l'admin qui agit est lui-même un admin actif) ; il reste comme garde-fou.
- `seed_roles.py` resynchronise les permissions des rôles listés : sur une base partagée avec un projet qui a ses propres permissions (ex. `jobs:classify`), les ajouter dans `PERMISSIONS` / `ROLES` avant de le lancer.
