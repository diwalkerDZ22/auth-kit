# Sprint3: Format des erreurs et logs

## Contexte

Le backend d’authentification est prêt pour un premier frontend (`http://localhost:5173`), mais ses réponses d’erreur ont plusieurs formes :

```json
{"detail": "Incorrect username or password"}                    // chaîne, en anglais
{"detail": {"code": "email_not_verified", "message": "..."}}    // objet
{"detail": [{"loc": ["body","email"], "msg": "...", ...}]}      // 422 FastAPI, en anglais
{"error": "Rate limit exceeded: 10 per 15 minute"}              // 429 slowapi
```

Le frontend ne peut pas s’appuyer sur un texte libre pour décider quoi afficher. Il lui faut un **code stable** et un **message en français** prêt à afficher.

Objectif de ce sprint :

1. **Un seul format d’erreur** pour toute l’API, y compris les erreurs produites par FastAPI et slowapi.
2. **Un catalogue de codes** documenté, utilisable par le frontend.
3. **Des logs propres** : `logging` à la place de `print()`, sans adresse email dans les logs.

---

## Choix retenus

| Choix | Raison |
|--------|--------|
| Format à plat `{"code", "message"}` | Plus simple à lire côté frontend que `{"detail": {...}}` |
| `code` en `snake_case` anglais, `message` en français | Le code est un identifiant technique stable, le message est pour l’utilisateur |
| Catalogue centralisé dans `app/core/errors.py` | Un seul endroit pour les codes, les statuts HTTP et les messages |
| `raise ApiError("code")` dans les routes | Plus de `HTTPException(detail=...)` écrit à la main |
| Gestionnaires globaux | Les 404/405/422/429/500 générés par les librairies sortent au même format |
| 409 pour les conflits d’inscription | 400 est réservé aux données invalides ; un username pris est un conflit |
| Succès : clé `message` (plus `detail`) | Même vocabulaire que les erreurs et que `/logout` |
| `logging` (logger `app.*`) | Niveaux, format, désactivable ; `print()` ne l’est pas |
| Pas d’email dans les logs | Donnée personnelle ; l’`id` et le `username` suffisent pour déboguer |

---

## Format cible

Erreur :

```json
{"code": "invalid_credentials", "message": "Identifiant ou mot de passe incorrect."}
```

Erreur de validation (422), avec le détail par champ :

```json
{
  "code": "validation_error",
  "message": "Certaines données sont invalides.",
  "fields": {"email": "Adresse email invalide.", "password": "Champ obligatoire."}
}
```

Réponse intermédiaire (succès, mais action attendue) :

```json
{"code": "login_email_sent", "attempt_id": "...", "message": "Un lien de connexion vient d’être envoyé à votre adresse email."}
{"code": "login_pending", "message": "En attente de la confirmation par email."}
```

---

## Catalogue des codes

### Erreurs génériques (gestionnaires globaux)

| Code | HTTP | Quand |
|------|------|-------|
| `validation_error` | 422 | Corps / formulaire / paramètres invalides (avec `fields`) |
| `rate_limited` | 429 | Limite slowapi dépassée |
| `not_authenticated` | 401 | Header `Authorization` absent |
| `forbidden` | 403 | Refus générique levé par une librairie |
| `not_found` | 404 | Route inconnue |
| `method_not_allowed` | 405 | Mauvaise méthode HTTP |
| `http_error` | autre | Toute autre `HTTPException` de librairie |
| `internal_error` | 500 | Exception non prévue (aucun détail interne exposé) |

### Routes protégées (`get_current_user`, `require_permission`)

| Code | HTTP | Quand |
|------|------|-------|
| `invalid_token` | 401 | Access token invalide, expiré, ou refresh token utilisé comme access token |
| `account_disabled` | 403 | `user.disabled` |
| `email_not_verified` | 403 | `is_verified=False` |
| `permission_denied` | 403 | Permission absente du rôle |

### `POST /auth/token`

| Code                  | HTTP| Quand |
|------                 |---- |-------|
| `invalid_credentials` | 401 | Username ou mot de passe faux (message générique) |
| `account_disabled` | 403 | Compte désactivé |
| `email_not_verified` | 403 | Inscription pas encore confirmée |
| `login_email_cooldown` | 429 | Un mail de login a été envoyé il y a moins d’une minute |
| `login_email_sent` | 202 | Succès : lien envoyé, `attempt_id` fourni |

### `POST /auth/refresh`

| Code | HTTP | Quand |
|------|------|-------|
| `invalid_refresh_token` | 401 | Token invalide, expiré, ou remplacé par un plus récent |
| `account_not_allowed` | 403 | Compte désactivé ou non vérifié |

### `POST /auth/login/claim`

| Code | HTTP | Quand |
|------|------|-------|
| `login_pending` | 202 | Lien pas encore cliqué : continuer à interroger |
| `login_attempt_unknown` | 410 | `attempt_id` inconnu ou déjà utilisé |
| `login_link_expired` | 410 | Lien expiré ou remplacé par une nouvelle tentative |
| `login_approval_expired` | 410 | Approuvé il y a plus de 2 minutes |
| `account_not_allowed` | 403 | Compte désactivé ou non vérifié |

### `POST /auth/register`

| Code | HTTP | Quand |
|------|------|-------|
| `username_taken` | 409 | Username déjà utilisé |
| `email_taken` | 409 | Email déjà utilisé |
| `account_exists` | 409 | Conflit détecté par la base (inscriptions simultanées) |

### `POST /auth/verify`

| Code | HTTP | Quand |
|------|------|-------|
| `invalid_link` | 400 | Lien inconnu, déjà utilisé ou expiré |
| `account_not_allowed` | 403 | Lien de login pour un compte désactivé ou non vérifié |

### Mot de passe et profil (Sprint 5)

| Code | HTTP | Quand |
|------|------|-------|
| `invalid_link` | 400 | `/auth/password/reset` : lien inconnu, déjà utilisé ou expiré |
| `account_disabled` | 403 | `/auth/password/reset` : compte désactivé |
| `invalid_current_password` | 400 | `/auth/password/change` : mot de passe actuel faux |
| `validation_error` | 422 | Nouveau mot de passe refusé (`fields.new_password`) |
| `email_unavailable` | 503 | `/auth/token` : le mail de login n'a pas pu partir |

### Administration (Sprint 5)

| Code | HTTP | Quand |
|------|------|-------|
| `user_not_found` | 404 | Utilisateur inconnu |
| `role_not_found` | 400 | Rôle inconnu |
| `cannot_modify_self` | 400 | Un admin modifie son propre compte |
| `last_admin` | 409 | Retirer ou désactiver le dernier admin actif (garde-fou) |

---

## Étapes de mise en œuvre

### 1. Module `app/core/errors.py`

- `ERRORS` : dictionnaire `code -> (statut HTTP, message)`.
- `ApiError(code, message=None, headers=None, **extra)` : exception métier. `extra` est ajouté au JSON (ex. `fields`).
- `register_error_handlers(app)` : enregistre les gestionnaires pour `ApiError`, `HTTPException` (Starlette), `RequestValidationError`, `RateLimitExceeded` et `Exception`.
- Traduction des erreurs Pydantic les plus courantes (`missing`, email invalide, type incorrect, JSON invalide) ; message générique sinon.

### 2. Remplacer les `HTTPException` dans les routes

`auth.py`, `login.py`, `register.py` : `raise ApiError("code")`. Garder le header `WWW-Authenticate: Bearer` sur les 401.

### 3. Réponses de succès

- `202` de `/auth/login/claim` : `{"code": "login_pending", "message": ...}` au lieu de `{"status": "pending"}`.
- `/auth/verify` et `/auth/resend-verification` : clé `message` au lieu de `detail`.
- Page HTML de test `GET /auth/verify` : lire `message`.

### 4. Logs

- `logging.getLogger(__name__)` dans chaque module, configuré dans `main.py` (logger `app`, niveau `LOG_LEVEL`, défaut `INFO`).
- Remplacer tous les `print()` de l’app par `logger.info` / `logger.warning`.
- Ne jamais logger d’email, de mot de passe ni de token ; utiliser l’`id` ou le `username`.

### 5. Nettoyage

- Retirer les imports inutilisés (`UserOut` dans `auth.py`, doublons dans `login.py`).

---

## Tests

- Mauvais mot de passe → 401 `invalid_credentials`
- Refresh token sur `/auth/me` → 401 `invalid_token`
- Sans header `Authorization` → 401 `not_authenticated`
- User sans permission → 403 `permission_denied`
- Register username pris → 409 `username_taken` ; email pris (casse différente) → 409 `email_taken`
- Register email mal formé → 422 `validation_error` avec `fields.email`
- `/auth/verify` lien faux → 400 `invalid_link`
- 11 × `/auth/verify` → 429 `rate_limited`
- Route inconnue → 404 `not_found`
- `/auth/login/claim` attempt inconnu → 410 `login_attempt_unknown`
- Aucun `print()` restant dans `app/`

---

## Critères de done

- [x] Toutes les erreurs de l’API ont la forme `{"code", "message"}` (+ `fields` pour 422)
- [x] Catalogue `ERRORS` centralisé et identique à ce document
- [x] Gestionnaires globaux pour 404 / 405 / 422 / 429 / 500
- [x] Messages en français partout
- [x] Réponses intermédiaires `login_email_sent` et `login_pending` avec un `code`
- [x] `logging` à la place de `print()`, sans email dans les logs
- [x] Imports inutilisés retirés
