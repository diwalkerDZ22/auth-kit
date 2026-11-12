# auth-kit

Authentification et autorisation réutilisables, en bibliothèque :

- **Backend** : package Python `auth-kit` pour FastAPI (`backend/`).
- **Frontend** : package npm `@auth-kit/react` (`frontend/packages/auth-kit/`), avec trois niveaux : client HTTP, hooks React sans interface, pages prêtes à l'emploi (thème clair / sombre).
- **Démo** : `backend/example/` et `frontend/apps/demo/` montrent l'intégration dans un projet.

Né dans le projet FakeJobApplicationRecognition, puis extrait pour servir de base à d'autres projets.

## Fonctionnalités

- Inscription avec vérification de l'email, sans révéler si une adresse est déjà inscrite
- Connexion en deux étapes : mot de passe, puis lien email qui indique l'heure, l'IP et le navigateur, avec « Ce n'est pas moi »
- Sessions par appareil : refresh token opaque en cookie httpOnly, stocké hashé, tournant, détection de réutilisation ; liste et déconnexion des appareils
- Mot de passe oublié, changement de mot de passe, mots de passe fuités refusés (Have I Been Pwned, optionnel)
- Rôles et permissions, administration des comptes
- Rate-limit par IP et par compte (mémoire ou Redis), temps de réponse constant au login
- Fonctionnalités optionnelles, textes, mails, codes d'erreur et rôles personnalisables par le projet
- Format d'erreur unique `{"code", "message"}`, types frontend générés depuis l'OpenAPI

## Démarrer la démo

```bash
cd backend
python -m pip install -r requirements.txt     # installe aussi le kit en mode éditable
cp .env.example .env                          # remplir AUTH_SECRET_KEY (et RESEND_API_KEY, ou EMAIL_BACKEND=console)
alembic upgrade head
auth-kit seed-roles
python -m uvicorn --factory example.main:create_app --reload   # Swagger : http://127.0.0.1:8000/docs
```

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, /api est relayé vers le backend
```

En dev : `EMAIL_BACKEND=console` écrit les liens dans les logs du backend, `AUTH_LOGIN_EMAIL_REQUIRED=false` permet de se connecter depuis Swagger, `AUTH_COOKIE_SECURE=false` en HTTP.

Premier admin : s'inscrire, puis donner le rôle `admin` en base (l'administration ne permet pas de se promouvoir soi-même).

## Utiliser le kit dans un projet

Voir **[docs/Bibliotheque.md](docs/Bibliotheque.md)** : installation, intégration en quelques lignes, fonctionnalités optionnelles, personnalisation, migrations Alembic, thème, et migration d'un projet existant.

## Tests

```bash
cd backend && python -m pip install -r requirements-dev.txt && python -m pytest
cd frontend && npm test && npm run lint && npm run build
```

## Documentation

Documents de conception (en français) dans `docs/` :

- `Bibliotheque.md` : le kit en bibliothèque (Sprint 8), guide d'intégration
- `Sprint7-Sessions-et-durcissement.md` : sessions par appareil, refus de connexion, rate-limit par compte, déploiement
- `Sprint6-Frontend.md` : frontend React, cookie httpOnly, CSRF
- `Sprint5-Auth-complete.md` : mot de passe oublié, profil, administration, révocation
- `Sprint3-Format-erreurs.md` : format d'erreur et catalogue des codes
- `Sprint2-Verification-mail.md`, `Sprint1-Ajout-des-roles.md`
- `Journal.md` : historique, opérations sur la base Supabase, points ouverts

Les documents des sprints 1 à 7 décrivent le comportement ; les chemins de fichiers qu'ils citent (`app/...`) sont ceux d'avant le Sprint 8.
