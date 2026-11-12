# Sprint 7 : sessions par appareil et durcissement

Suite de la revue complète du kit. Objectifs : plusieurs appareils connectés en même temps, plus de déconnexions intempestives entre onglets, plus aucun secret de session en clair dans la base, et fermeture des petites fuites d'information.

## Changements incompatibles

| Avant | Maintenant | À faire dans un projet consommateur |
|-------|------------|-------------------------------------|
| `from app.api.auth import require_permission` | `from app.api.deps import require_permission` | Mettre à jour l'import (idem `get_current_user`, `get_current_active_user`) |
| `api.auth.new_password_error` | `core.password_policy.new_password_error` | Mettre à jour l'import |
| `crud.user.bump_token_version(user)` | `crud.user.revoke_all_sessions(user)` | Renommer l'appel |
| `core.tokens.issue_session(db, user, response)` | `core.sessions.issue_session(db, user, request, response)` | Passer aussi `request` |
| `POST /auth/register` → `UserOut` | → `{"message"}` (201), même réponse si l'email est déjà inscrit | Ne plus lire `id` / `email` dans la réponse |
| Code `email_taken` (409) | Supprimé | Rien : le titulaire de l'adresse reçoit un mail |
| `users.refresh_token` | Supprimée (table `user_sessions`) | `alembic upgrade head` ; chacun se reconnecte une fois |
| `GET /auth/verify` (page HTML de test) toujours servie | `VERIFY_TEST_PAGE=true` requis | L'activer dans le `.env` de dev si besoin |
| `python-jose`, `passlib` | `pyjwt`, `bcrypt` (épinglés) | `pip install -r requirements.txt`. Les hashes existants restent valides |

## Sessions par appareil

Avant : un seul refresh token par utilisateur (`users.refresh_token`, en clair). Se connecter sur le téléphone déconnectait l'ordinateur.

Maintenant, chaque connexion crée une ligne `user_sessions` :

| Colonne | Rôle |
|---------|------|
| `id` | Aléatoire, repris dans le claim `sid` de l'access token |
| `token_hash` | SHA-256 du refresh token courant (cookie). Le token lui-même n'est jamais stocké |
| `previous_token_hash`, `rotated_at` | Token précédent : délai de grâce et détection de réutilisation |
| `ip`, `user_agent` | Affichés dans « Appareils connectés » |
| `created_at`, `last_used_at`, `expires_at`, `revoked_at` | Cycle de vie |

- Le refresh token est une valeur aléatoire opaque (plus un JWT) : la base suffit à le valider.
- L'access token porte `sub`, `ver` (= `token_version`) et `sid`. `get_current_user` refuse le token si la version a changé **ou** si la session est fermée ou expirée.
- `/auth/logout` ne ferme que la session du cookie. `revoke_all_sessions()` (mot de passe, désactivation, changement de rôle) ferme tout.
- Expiration glissante : chaque refresh repousse `expires_at` de `REFRESH_TOKEN_EXPIRE_DAYS`.

### Refresh : rotation, délai de grâce, réutilisation

| Token présenté | Résultat |
|----------------|----------|
| Courant | Rotation : nouveau cookie, access token neuf |
| Précédent, remplacé il y a ≤ `REFRESH_REUSE_GRACE_SECONDS` (30 s) | Access token neuf, **cookie inchangé** (le navigateur a déjà le nouveau) |
| Précédent, plus ancien | Réutilisation d'un token volé probable : session révoquée, 401 |
| Inconnu, session fermée ou expirée | 401 `invalid_refresh_token`, cookie effacé |

### Plusieurs onglets

Le cookie est partagé par tous les onglets. Si deux onglets rafraîchissent en même temps, le second envoie l'ancien token. Avant, ça déconnectait tout le monde. Deux protections :

1. Frontend : `refreshSession()` prend un verrou du navigateur (`navigator.locks`, nom `auth-kit-refresh`). Le second onglet attend, puis part avec le cookie déjà renouvelé.
2. Backend : le délai de grâce ci-dessus, pour les navigateurs sans Web Locks et les requêtes qui se croisent sur le réseau.

### Nouvelles routes

| Méthode | Route | Accès | Effet |
|---------|-------|-------|-------|
| GET | `/auth/sessions` | Bearer | Sessions actives, `current: true` pour celle de la requête |
| DELETE | `/auth/sessions/{id}` | Bearer | Ferme un appareil (404 `session_not_found` si inconnu, fermé ou à un autre compte) |
| DELETE | `/auth/sessions` | Bearer | Ferme tous les autres appareils, renvoie `count` |

Côté frontend : section « Appareils connectés » dans `ProfilePage`, `authApi.listSessions()`, `revokeSession(id)`, `revokeOtherSessions()`.

## Connexion par email : contexte et refus

- Le mail de connexion indique la date (UTC), l'adresse IP et le navigateur de la demande.
- Le lien porte `&type=login` (pas un secret). La page `/verify-email` propose alors « Oui, c'est moi » et « Ce n'est pas moi ».
- `POST /auth/login/deny` `{ "token" }` consomme le lien sans approuver. La page de l'attaquant reçoit `login_link_expired` et l'utilisateur est invité à changer son mot de passe.
- `set_password()` (changement et reset) annule aussi les liens de login et de reset encore actifs : une tentative lancée avec l'ancien mot de passe ne peut plus aboutir.

## Fuites d'information

- **Temps de réponse du login** : pour un username inconnu, `authenticate_user` fait quand même un calcul bcrypt (`burn_password_check`). La durée ne révèle plus si le compte existe.
- **Inscription** : un username pris reste signalé (`username_taken`), c'est inévitable puisqu'on le choisit. Pour un email déjà inscrit, la réponse est identique à une inscription réussie, le mot de passe est quand même hashé (même durée) et le titulaire reçoit un mail « tentative d'inscription avec votre adresse », au plus 1 par 30 min et par adresse.

## Rate-limit

- **Par compte** : `LOGIN_FAILURES_PER_ACCOUNT` (10 / 15 min) échecs de mot de passe par username, toutes IP confondues. Une fois la limite atteinte, la connexion est refusée (429 `rate_limited`) même avec le bon mot de passe, jusqu'à la fin de la fenêtre. C'est le compromis habituel : une attaque répartie est arrêtée, au prix d'un blocage temporaire du compte visé.
- **Stockage** : `RATE_LIMIT_STORAGE_URI` (`memory://` par défaut). Avec plusieurs workers ou serveurs, utiliser Redis (`redis://host:6379`), sinon chaque process a ses propres compteurs.
- **Derrière un reverse proxy** : lancer uvicorn avec `--proxy-headers --forwarded-allow-ips=<ip du proxy>`. Sinon tous les clients ont l'IP du proxy et partagent la même limite (et la même IP dans « Appareils connectés »).

## Mots de passe

- `PASSWORD_BREACH_CHECK=true` refuse les mots de passe présents dans Have I Been Pwned. Seuls les 5 premiers caractères du SHA-1 quittent le serveur (k-anonymity, avec `Add-Padding`). Si l'API est injoignable, le mot de passe est accepté et un warning est loggé. Désactivé par défaut dans `Settings` (tests hors ligne), activé dans `.env.example`.
- `bcrypt` 5 refuse les mots de passe de plus de 72 octets : `verify_password` renvoie `False` au lieu de lever une exception.

## Déploiement

| Situation | Réglages |
|-----------|----------|
| Frontend et API sur la même origine (proxy `/api`, comme en dev) | Rien de spécial, `COOKIE_SAMESITE=strict` |
| Même site, sous-domaines différents (`app.exemple.com` / `api.exemple.com`) | `VITE_API_BASE=https://api.exemple.com`, origine du frontend dans `CORS_ORIGINS`. `strict` fonctionne (même site) |
| Sites différents | `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`, origine dans `CORS_ORIGINS`. Les navigateurs qui bloquent les cookies tiers casseront le refresh : préférer un proxy |

Le header `X-CSRF-Protection` est désormais dans `allow_headers` du CORS : sans lui, `/auth/refresh` et `/auth/logout` échouaient au preflight dès que le frontend était sur une autre origine.

Autres réglages :

- `DATABASE_SSLMODE` : `require` par défaut pour PostgreSQL, `disable` pour un Postgres local sans SSL. Un `sslmode=` présent dans `DATABASE_URL` l'emporte.
- `python -m scripts.cleanup [--days 7]` : supprime les liens email expirés et les sessions expirées ou fermées. À planifier (cron).

## Code

- Dépendances d'authentification dans `app/api/deps.py`.
- Routes regroupées par sujet dans `app/api/authentification/` : `login.py` (token, claim, deny), `sessions.py` (refresh, logout, appareils), `register.py`, `account.py` (`/me`, changement de mot de passe), `password.py` (oublié / reset).
- Supprimés : `api/auth.py`, `core/tokens.py`, schémas `Token`, `TokenData`, `TokenPair`, `UserOut`, fonctions `save_refresh_token`, `revoke_refresh_token`, `create_refresh_token`.
- Recherche admin : `%` et `_` sont cherchés tels quels (échappés dans le `LIKE`).
- Dernier admin : les lignes des admins sont verrouillées (`FOR UPDATE`) pendant la vérification, deux retraits simultanés ne peuvent plus laisser l'application sans admin.
- Versions des dépendances épinglées (`requirements*.txt`, et `vitest` / `happy-dom` côté frontend).

### Non fait volontairement

- **Fusion des migrations** : la base Supabase du projet d'origine (voir `Journal.md`) est déjà à ces révisions. Les fusionner casserait son `alembic_version`. Une base neuve les applique toutes sans problème.

## Tests

- Backend : `tests/test_sessions.py` (plusieurs appareils, logout ciblé, hash stocké, délai de grâce, réutilisation, expiration, liste et fermeture d'appareils, changement de mot de passe) et `tests/test_hardening.py` (refus de connexion, contexte du mail, limite par compte, temps constant, avis « compte existant », liens annulés, HIBP, bcrypt > 72 octets, recherche admin, page de test, CORS, `sslmode`, nettoyage).
- Frontend : `npm test` (Vitest + happy-dom). `src/auth/api.test.ts` couvre le refresh partagé, le verrou entre onglets, le header CSRF, le rejeu unique après `invalid_token` et les pannes réseau. `src/auth/forms.test.ts` couvre `safeNext` et la lecture des liens.
