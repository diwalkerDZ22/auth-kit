# Sprint2: Verification mail

## Contexte

Le service d’authentification (`auth_app` : FastAPI + JWT + SQLAlchemy + Alembic) crée un compte à l’inscription et délivre des tokens au login **sans confirmer que l’email appartient à l’utilisateur**.

Objectif de ce sprint : **vérifier l’email à l’inscription ET à chaque connexion**.

1. **Register** : créer le compte, envoyer un mail via **Resend**, compte inutilisable tant que l’email n’est pas confirmé (`is_verified=False`).
2. **Login** : mot de passe OK **ne suffit plus**. Un second mail (lien) est envoyé à **chaque** connexion ; les JWT ne sont émis **qu’après** ce clic.
3. **Refresh** : ne redemande **pas** un mail (session déjà ouverte). Si le compte n’a jamais été vérifié (`is_verified=False`), refresh refusé.
4. Endpoints **verify** (signup + login) et **resend**.

---

## Choix retenus

| Choix | Raison |
|--------|--------|
| Table `email_verifications` + `purpose` (`signup` / `login`) | Même infra, deux usages ; rotation, expiration, audit |
| Token `secrets.token_urlsafe(32)` | Lien cliquable, non bruteforçable (mieux qu’un OTP 6 chiffres) |
| Hash SHA-256 en DB | Une fuite de DB ne donne pas de liens valides |
| 1 seul token **actif par user et par purpose** | Un resend signup n’annule pas un challenge login, et inversement |
| **Resend** (API HTTP, pas SMTP) | Envoi unique pour signup et login |
| Pas de JWT avant verify **signup** ni avant verify **login** | Double confirmation réelle |
| Expiration signup 24h / login 15 min | Le challenge de connexion doit être court |

À **ne pas** faire : JWT dès le password OK, token en clair sur `User`, SMTP Gmail, JWT dans le mail, redemander un mail à chaque `/auth/refresh`.

---

## État actuel (rappel)

| Élément | Détail |
|--------|--------|
| Register | `POST /auth/register` — crée le user, pas de mail, pas de `is_verified` |
| Login | `POST /auth/token` — JWT dès que username/password OK |
| Refresh | `POST /auth/refresh` — pas de check email |
| User | `id`, `username`, `email`, `full_name`, `hashed_password`, `disabled`, `refresh_token`, `role_id` |
| Mail | Aucun (pas de Resend, pas de SMTP) |

Fichiers clés :

- `auth_app/app/api/auth.py` — routes + dépendances
- `auth_app/app/db/models.py` — modèle `User`
- `auth_app/app/crud/user.py` — `create_user` / `authenticate_user`
- `auth_app/app/schemas/user.py` — `UserCreate` / `UserOut`
- `auth_app/app/core/config.py` — settings / `.env`
- `auth_app/app/core/security.py` — hash / JWT
- `auth_app/requirements.txt`

---

## Flux cible

```text
POST /register
  → User(is_verified=False)
  → token purpose=signup
  → Resend : lien d’activation
  → pas de JWT

POST /auth/verify  { token }   (purpose=signup)
  → is_verified=True
  → toujours pas de JWT (il faudra se connecter)

POST /auth/token  (username + password)
  → si identifiants KO          → 401 (message générique)
  → si is_verified=False        → 403 Email not verified
  → si OK                       → token purpose=login + mail Resend
                                → 202, PAS de JWT

POST /auth/verify  { token }   (purpose=login)
  → access_token + refresh_token

POST /auth/resend-verification
  → selon purpose (signup ou login), invalide l’ancien token du même purpose
  → nouveau mail Resend
  → toujours 200 générique

POST /auth/refresh
  → JWT seulement si is_verified=True (pas de nouveau mail)
```

Chaque **nouvelle** tentative de login invalide le challenge login précédent.

---

## Étapes de mise en œuvre

### 1. Compte Resend

1. Créer un compte sur [resend.com](https://resend.com)
2. En **dev** : `onboarding@resend.dev` (envoi seulement vers **ton** email Resend)
3. En **prod** : domaine vérifié (SPF/DKIM), `noreply@ton-domaine.com`
4. API key → `RESEND_API_KEY` (jamais commitée)

---

### 2. Dépendances et config

Ajouter `resend` et `slowapi` dans `auth_app/requirements.txt`.

`.env` / `config.py` :

```env
RESEND_API_KEY=re_xxxx
MAIL_FROM=onboarding@resend.dev
MAIL_FROM_NAME=FakeJob Auth
FRONTEND_VERIFY_URL=http://localhost:3000/verify-email
SIGNUP_TOKEN_EXPIRE_HOURS=24
LOGIN_TOKEN_EXPIRE_MINUTES=15
```

Sans frontend, `FRONTEND_VERIFY_URL` peut pointer vers `http://127.0.0.1:8000/auth/verify`.

---

### 3. Modèle DB

Sur `User` : `is_verified = Column(Boolean, default=False, nullable=False)`.

Table unique :

```text
email_verifications
  id
  user_id          FK users ON DELETE CASCADE
  purpose          "signup" | "login"
  token_hash       unique (sha256 du token envoyé)
  expires_at
  used_at          nullable
  created_at
```

Règle : au plus **un** token non utilisé par couple `(user_id, purpose)`.

Migration Alembic. Users déjà en base : `is_verified=True` (le signup est considéré fait ; le **login** demandera quand même un mail à chaque connexion).

`UserOut` : exposer `is_verified`.

---

### 4. Module d’envoi Resend

Nouveau fichier `auth_app/app/core/email.py` : deux templates (même API Resend).

- **Signup** : « Confirmez votre adresse email » + lien d’activation (24h)
- **Login** : « Confirmez cette connexion » + lien (15 min)

Exemple :

```python
import resend
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY

def send_verification_email(to: str, verify_url: str, purpose: str) -> None:
    if purpose == "login":
        subject = "Confirmez cette connexion"
        body = f"<p>Une connexion a été demandée. Cliquez pour continuer :</p>"
    else:
        subject = "Confirmez votre adresse email"
        body = f"<p>Cliquez pour activer votre compte :</p>"

    resend.Emails.send({
        "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": f"""
          {body}
          <p><a href="{verify_url}">{verify_url}</a></p>
          <p>Si vous n’êtes pas à l’origine de cette demande, ignorez ce mail.</p>
        """,
    })
```

Si Resend est down :

- **register** : créer le user quand même, logger, l’utilisateur utilise `/resend-verification` (`purpose=signup`)
- **login** : ne pas faire croire que le challenge est parti ; **503** ou message « impossible d’envoyer le mail, réessayez »

Ne jamais mettre le mot de passe dans le mail.

---

### 5. Tokens

Helper `auth_app/app/core/verification.py` :

1. `raw = secrets.token_urlsafe(32)`
2. `token_hash = hashlib.sha256(raw.encode()).hexdigest()`
3. Invalider les tokens **non utilisés** du même `(user_id, purpose)`
4. `expires_at` = 24h si `signup`, 15 min si `login`
5. Lien : `{FRONTEND_VERIFY_URL}?token={raw}`
6. Envoyer le **raw** par mail uniquement

`POST /auth/verify` :

1. Hasher le token reçu
2. Ligne `token_hash` + `used_at is None` + `expires_at > now`
3. Marquer `used_at`
4. Si `purpose=signup` → `is_verified=True`, **pas** de JWT
5. Si `purpose=login` → contrôler `is_verified=True`, puis émettre access + refresh (comme aujourd’hui après `/token`)

---

### 6. Register

1. Unicité username / email (déjà fait)
2. `create_user` avec `is_verified=False`
3. Token `purpose=signup` + mail Resend
4. **201** + `UserOut` — **pas de JWT**

---

### 7. Login (changement majeur)

`POST /auth/token` **ne retourne plus** `TokenPair`.

Après `authenticate_user` :

```text
identifiants KO        → 401 Incorrect username or password
user.disabled          → 400 Inactive user
not is_verified        → 403 Email not verified
                       (doit d’abord /auth/verify signup)
sinon                  → créer challenge purpose=login
                       → mail Resend
                       → 202 { "message": "Verification email sent" }
```

Ne pas révéler si le username existe au-delà du 401 habituel déjà en place.

Réponse 202 volontairement **sans** `user_id` / email (anti-énumération).

---

### 8. Routes

| Méthode | Path | Auth | Comportement |
|---------|------|------|----------------|
| POST | `/auth/register` | public | Compte + mail signup, pas de JWT |
| POST | `/auth/verify` | public | `{ "token" }` : signup → compte activé ; login → **TokenPair** |
| POST | `/auth/resend-verification` | public | `{ "email", "purpose": "signup"\|"login" }` — **toujours 200** générique |
| POST | `/auth/token` | public | Password OK + `is_verified` → mail login, **202 sans JWT** |
| POST | `/auth/refresh` | refresh | Tokens si `is_verified` ; **pas** de nouveau mail |
| POST | `/auth/logout` | Bearer | Inchangé |

Resend :

- `purpose=signup` : seulement si user existe et `is_verified=False`
- `purpose=login` : seulement si user existe, `is_verified=True`, et un challenge login encore valide **ou** on en recrée un (invalide l’ancien)
- Email inconnu / déjà vérifié (signup) / non vérifié (login) → même 200 : *« Si un compte existe, un email a été envoyé. »*

---

### 9. Refresh

Le refresh **n’est pas** une nouvelle connexion : pas d’email.

- `is_verified=False` → 403
- sinon rotation des tokens comme aujourd’hui

`get_current_active_user` : refuser aussi `not is_verified`.

---

### 10. Rate-limit

- register / resend signup : ~3 / email / 15 min
- login (`/token`) : ~5 / username / 15 min (chaque login envoie un mail)
- resend login : ~3 / email / 15 min
- verify : ~10 / IP / 15 min

Librairie : `slowapi`.

---

### 11. Sécurité

| Point | Pourquoi |
|--------|----------|
| Token long + hash | Pas de brute-force ni fuite utile |
| Signup 24h / login 15 min | Challenge de connexion court |
| Un token actif par purpose | Ancien lien login mort dès une nouvelle tentative |
| Rate-limit | Coût Resend + anti-spam |
| Réponses génériques resend | Pas d’énumération d’emails |
| Pas de JWT avant verify login | Vol de mot de passe ≠ session sans accès à la boîte mail |
| Refresh sans mail | UX session normale une fois le login confirmé |

---

## Ordre de mise en œuvre

1. `resend` + variables d’env (TTL signup vs login)
2. Migration : `is_verified` + `email_verifications.purpose`
3. `email.py` (2 templates) + `verification.py`
4. Register + verify signup
5. Transformer `/auth/token` en « envoi du mail de connexion »
6. Verify login → émission des JWT
7. Resend selon `purpose`
8. Refresh : check `is_verified` seulement
9. Rate-limit
10. Tests

---

## Tests

- Register → 201, `is_verified=False`, pas de JWT
- Verify signup → `is_verified=True`, pas de JWT
- `/token` avant signup verify → 403
- `/token` après signup verify → 202, **pas** de JWT, mail login
- Verify login → 200 + `TokenPair`
- Nouveau `/token` invalide l’ancien lien login
- Token login expiré / déjà utilisé → 400
- Refresh sans never-verified → 403
- Refresh après login verify → 200, **sans** envoyer de mail
- Resend email inconnu → 200 générique

---

## Critères de done

- [ ] `is_verified` + table `email_verifications` avec `purpose`
- [ ] Migration Alembic (users existants `is_verified=True`)
- [ ] Envoi Resend : mail signup **et** mail login
- [ ] Token hashé, usage unique, TTL selon purpose, rotation
- [ ] Register n’émet pas de JWT
- [ ] `/auth/token` n’émet pas de JWT : envoie un mail à **chaque** connexion
- [ ] `/auth/verify` active le compte (signup) ou délivre les JWT (login)
- [ ] Refresh sans nouveau mail, refusé si jamais vérifié
- [ ] Resend par purpose, réponses génériques
- [ ] Rate-limit
- [ ] Tests signup + login challenge + refresh

---

## Bilan du sprint (2026-11-11)

### Fait

- [x] `is_verified` + table `email_verifications` avec `purpose`
- [x] Migration Alembic (users existants `is_verified=True`)
- [x] Envoi Resend : mail signup **et** mail login
- [x] Token hashé, usage unique, TTL selon purpose, rotation
- [x] Register n’émet pas de JWT
- [x] `/auth/token` n’émet pas de JWT : envoie un mail à chaque connexion (sauf `LOGIN_EMAIL_REQUIRED=false`, dev uniquement)
- [x] `/auth/verify` active le compte (signup) ou approuve la connexion (login)
- [x] Refresh sans nouveau mail, refusé si non vérifié ou désactivé
- [x] Resend signup avec réponse générique
- [x] Rate-limit (commit `db36336`)

### Écarts volontaires par rapport au plan

| Plan | Réalisé | Raison |
|------|---------|--------|
| Verify login → `TokenPair` | Verify login pose seulement `approved_at` ; la page d’origine récupère les tokens via `POST /auth/login/claim` (`attempt_id`, 2 min après approbation) | Le lien peut être ouvert sur un autre appareil : les tokens ne vont qu’à la page qui a fait la demande |
| `user.disabled` → 400 Inactive user | 403 « Compte désactivé » | Cohérent avec les autres refus d’accès |
| Rate-limit par username / email | Rate-limit par IP (slowapi, stockage mémoire) | Lire le corps de la requête dans `key_func` est fragile ; à revoir en prod (Redis) |

### Reste à faire

- [ ] **Resend down au login** : l’envoi est une `BackgroundTask`, donc `/auth/token` répond 202 même si Resend échoue. Le plan prévoyait un 503. Il faut envoyer le mail de login de façon synchrone (ou vérifier le résultat) avant de répondre.
- [ ] **Resend par purpose** : `/auth/resend-verification` ne gère que `signup`. Pour le login, relancer `/auth/token` fait office de renvoi ; décider si une route dédiée est utile.
- [ ] **Tests** : aucun des tests listés plus haut n’est écrit (`TestClient` demande le paquet `httpx2`).
- [ ] **SQLite** : `.env.example` propose SQLite, qui renvoie des dates sans fuseau ; les comparaisons de `created_at` (anti-spam login et resend) peuvent planter. Postgres n’est pas concerné.
- [ ] **Email de login plus informatif** : afficher IP / heure / navigateur pour limiter les approbations par réflexe (phishing).
