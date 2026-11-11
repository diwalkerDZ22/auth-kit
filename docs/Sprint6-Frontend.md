# Sprint6: Frontend React

## Contexte

Le backend d’`auth-kit` est complet (Sprints 1 à 5) mais n’a pas d’interface. Objectif de ce sprint : un frontend **React + TypeScript** qui couvre tout le parcours d’authentification, avec un **module d’auth réutilisable** qu’un autre projet peut copier tel quel.

Le refresh token passe dans un **cookie httpOnly** : le JavaScript ne peut pas le lire, donc une faille XSS ne peut pas voler la session. Cela demande des changements côté backend (partie A).

---

## Choix retenus

| Choix | Raison |
|--------|--------|
| Refresh token en cookie `httpOnly`, `SameSite=Strict`, `Secure` en prod | Inaccessible au JavaScript ; non envoyé par les autres sites |
| Access token en mémoire uniquement | Durée courte (30 min) ; perdu au rechargement, retrouvé via `/auth/refresh` |
| Header `X-CSRF-Protection: 1` obligatoire sur les routes qui lisent le cookie | Un autre site ne peut pas l’ajouter sans preflight CORS : seconde barrière après `SameSite` |
| Proxy `/api` → backend (Vite en dev, reverse proxy en prod) | Frontend et API sur la même origine : pas de CORS, cookie `SameSite=Strict` utilisable |
| Vite + React + TypeScript + React Router | Stack la plus courante, attendue sur `http://localhost:5173` |
| Tailwind CSS | Pas de composants imposés : chaque projet garde sa charte |
| TanStack Query | Cache et états de chargement des appels (`/auth/me`, admin) |
| React Hook Form + Zod | Formulaires typés ; règles reprises du backend pour un retour immédiat |
| Les erreurs `fields` du backend s’affichent sous les champs | Le backend reste la référence (mots de passe courants, conflits) |
| Module `src/auth/` sans dépendance vers le reste de l’app | C’est la partie réutilisable du kit |

À **ne pas** faire : stocker un token dans `localStorage` / `sessionStorage`, lire le refresh token en JavaScript, dupliquer les messages d’erreur du backend dans le frontend.

---

## Partie A : backend

### Cookie de refresh

| Réglage | Défaut | Rôle |
|---------|--------|------|
| `REFRESH_COOKIE_NAME` | `refresh_token` | Nom du cookie |
| `REFRESH_COOKIE_PATH` | `/` | Chemin du cookie (`/api/auth` derrière le proxy) |
| `COOKIE_SECURE` | `true` | `false` seulement en dev HTTP |
| `COOKIE_SAMESITE` | `strict` | `none` si le frontend est sur un autre site (avec `COOKIE_SECURE=true`) |

### Routes modifiées

| Route | Avant | Après |
|-------|-------|-------|
| `POST /auth/login/claim` | `TokenPair` | `AccessToken` + cookie |
| `POST /auth/token` (mode dev sans mail) | `TokenPair` | `AccessToken` + cookie |
| `POST /auth/password/change` | `TokenPair` | `AccessToken` + cookie |
| `POST /auth/refresh` | corps `{refresh_token}` | lit le cookie, header CSRF obligatoire ; renvoie `AccessToken` + nouveau cookie |
| `POST /auth/logout` | Bearer obligatoire | lit le cookie (marche même avec un access token expiré), header CSRF obligatoire ; efface le cookie |

`AccessToken` = `{ "access_token", "token_type": "bearer", "expires_in" }` (secondes). Le refresh token n’apparaît plus jamais dans un corps de réponse.

### Nouveau code d’erreur

| Code | HTTP | Quand |
|------|------|-------|
| `csrf_missing` | 403 | Header `X-CSRF-Protection` absent sur `/auth/refresh` ou `/auth/logout` |

`/auth/refresh` sans cookie ou avec un cookie invalide : `invalid_refresh_token` (401), cookie effacé.

---

## Partie B : frontend

### Structure

```text
frontend/
  vite.config.ts           proxy /api -> http://127.0.0.1:8000
  src/
    auth/                  module réutilisable
      api.ts               client fetch : access token en mémoire, refresh automatique
      errors.ts            classe ApiError (code, message, fields)
      types.ts             types des réponses du backend
      schemas.ts           schémas Zod (règles du Sprint 5)
      AuthProvider.tsx     contexte : user, statut, login, logout
      guards.tsx           RequireAuth, RequirePermission
      pages/               une page par étape du parcours
    app/                   coquille de démo (layout, accueil, routes)
```

### Client API

- Ajoute `Authorization: Bearer` si un access token est en mémoire.
- Sur un 401 `invalid_token` : un seul `/auth/refresh` partagé entre les requêtes en cours, puis rejoue la requête. Si le refresh échoue : session terminée.
- Toute réponse d’erreur devient une `ApiError` (`code`, `message`, `fields`).
- Au démarrage de l’app : `/auth/refresh` pour retrouver la session, puis `/auth/me`.

### Pages

| Route | Page |
|-------|------|
| `/login` | Mot de passe, puis attente du clic dans l’email (interrogation de `/auth/login/claim` toutes les 2 s) |
| `/register` | Inscription, puis « vérifiez votre boîte mail » (+ renvoi du mail) |
| `/verify-email` | Lien reçu par email : confirme l’inscription ou approuve la connexion |
| `/forgot-password` | Demande de lien de réinitialisation |
| `/reset-password` | Nouveau mot de passe depuis le lien |
| `/profile` | Nom complet, changement de mot de passe, déconnexion |
| `/admin/users` | Liste, recherche, pagination, changement de rôle, désactivation (`users:manage`) |

Le token d’un lien (`?token=`) est retiré de l’URL dès la lecture (historique, en-tête `Referer`).

---

## Ordre de mise en œuvre

1. Backend : réglages cookie, `AccessToken`, cookie sur les routes qui émettent des tokens
2. Backend : `/auth/refresh` et `/auth/logout` par cookie + CSRF ; tests mis à jour
3. Frontend : projet Vite + Tailwind + proxy
4. Module `auth` : erreurs, client API, provider, gardes
5. Pages : connexion, inscription, vérification, mot de passe oublié / reset
6. Pages : profil, administration
7. Vérification de bout en bout dans le navigateur

---

## Tests

Backend :

- `/auth/login/claim` pose le cookie, le corps ne contient pas de refresh token
- `/auth/refresh` sans header CSRF → 403 `csrf_missing` ; sans cookie → 401 `invalid_refresh_token`
- `/auth/refresh` avec cookie + header → nouvel access token et nouveau cookie ; l’ancien cookie est refusé
- `/auth/logout` avec un access token expiré mais un cookie valide → session coupée, cookie effacé

Frontend (dans le navigateur) :

- Inscription → mail → vérification → connexion → attente → tokens → profil
- Rechargement de la page : la session est retrouvée sans se reconnecter
- Access token expiré : refresh transparent
- Mot de passe oublié de bout en bout
- Erreurs `fields` affichées sous les bons champs
- Admin : recherche, désactivation, changement de rôle

---

## Critères de done

- [x] Refresh token uniquement en cookie httpOnly ; jamais dans un corps de réponse ni en `localStorage`
- [x] `/auth/refresh` et `/auth/logout` protégés par le header CSRF
- [x] Tests backend à jour et passés
- [x] Module `src/auth/` indépendant de `src/app/`
- [x] Toutes les pages du tableau fonctionnelles
- [x] Session retrouvée après rechargement, refresh transparent
- [ ] Parcours vérifiés dans le navigateur

---

## Bilan (2026-11-11)

- Backend : 21 tests pytest passés (cookie, CSRF, logout par cookie).
- Frontend : `npm run build` (TypeScript strict) et `npm run lint` (oxlint) sans erreur ni avertissement.
- Parcours complet joué **à travers le proxy Vite** (inscription → vérification → connexion par email → refresh par cookie → profil → mot de passe → logout → reset) : OK.
- **Reste à faire** : vérifier l’affichage des pages dans un vrai navigateur (l’extension Chrome n’était pas connectée).
- Backend relancé sur Supabase avec Resend pour un test manuel ; compte admin de test : `usertest` (voir `Journal.md`).

Ajout par rapport au plan :

| Ajout | Raison |
|-------|--------|
| `EMAIL_BACKEND=console` (dev uniquement) | Les liens sont écrits dans les logs : tester tout le parcours sans boîte mail. Seule exception à « pas de token dans les logs » |
| Page `/resend-verification` | Lien depuis la connexion quand l’email n’est pas vérifié |
| La page `/verify-email` demande un clic | Les antivirus qui ouvrent les liens des mails ne consomment pas le lien |
