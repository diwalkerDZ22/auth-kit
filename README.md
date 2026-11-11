# auth-kit

Module d'authentification réutilisable : backend FastAPI (JWT, rôles et permissions, vérification par email via Resend) et, à venir, frontend React + TypeScript.

Né dans le projet FakeJobApplicationRecognition, puis extrait pour servir de point de départ à d'autres projets.

## Fonctionnalités (backend)

- Inscription avec vérification de l'email (lien valable 24 h)
- Connexion en deux étapes : mot de passe, puis clic sur un lien reçu par email (15 min)
- Access token + refresh token (JWT HS256), déconnexion
- Rôles et permissions (`require_permission("code")`)
- Rate-limit sur les routes publiques
- Format d'erreur unique `{"code", "message"}` avec messages en français

## Démarrer le backend

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env            # remplir au minimum SECRET_KEY et RESEND_API_KEY
alembic upgrade head
python scripts/seed_roles.py    # crée les rôles et permissions
python -m uvicorn app.main:app --reload
```

Interface de test : http://127.0.0.1:8000/docs

En dev, `LOGIN_EMAIL_REQUIRED=false` dans `.env` permet de se connecter depuis Swagger sans l'étape email.

## Documentation

Les documents de conception (en français) sont dans `docs/` :

- `Sprint1-Ajout-des-roles.md`
- `Sprint2-Verification-mail.md`
- `Sprint3-Format-erreurs.md` : format d'erreur et catalogue des codes
