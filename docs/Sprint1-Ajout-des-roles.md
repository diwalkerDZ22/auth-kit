# Sprint1: Ajout des roles

## Contexte

Le service d’authentification actuel (`auth_app`) est basé sur **FastAPI + JWT + SQLAlchemy**. Il gère uniquement l’**identité** :

- authentifié / non authentifié ;
- actif / désactivé (`disabled`).

Il n’existe pas encore de rôles ni de permissions. L’objectif de ce sprint est d’ajouter une **gestion des rôles** dont le but est d’**attribuer des actions permises** à chaque rôle (RBAC).

Passer de :

- authentifié / non authentifié  

à :

- **rôle** → liste d’**actions** (permissions) → contrôle sur les routes

Exemple : rôle `analyst` → `jobs:classify`, `jobs:read` ; rôle `admin` → tout.

---

## État actuel de l’authentification (rappel)

| Élément | Détail |
|--------|--------|
| Stack | FastAPI, SQLAlchemy, PostgreSQL, python-jose (JWT), passlib/bcrypt |
| Login | `POST /auth/token` → access JWT + refresh JWT |
| Guards | `get_current_user` / `get_current_active_user` (dépendances FastAPI) |
| User | `id`, `username`, `email`, `full_name`, `hashed_password`, `disabled`, `refresh_token` |
| Autorisation | Aucune (pas de rôle / permission) |

Fichiers clés :

- `auth_app/app/api/auth.py` — routes + dépendances d’auth
- `auth_app/app/db/models.py` — modèle `User`
- `auth_app/app/core/security.py` — hash / JWT
- `auth_app/app/crud/user.py` — CRUD utilisateur
- `auth_app/app/schemas/user.py` — schémas Pydantic

---

## Objectif du sprint

Mettre en place un modèle **rôle → permissions (actions)** et des gardes pour protéger les endpoints selon les actions autorisées.

---

## Étapes de mise en œuvre

### 1. Modéliser rôles et permissions

Deux tables (recommandé) plutôt qu’un simple champ `role` sur `User` :

| Table | Rôle |
|--------|------|
| `permissions` | Actions atomiques : `code` unique (`jobs:classify`, `users:manage`, …) |
| `roles` | Ex. `admin`, `analyst`, `viewer` |
| `role_permissions` | Many-to-many rôle ↔ permissions |
| `user_roles` | Many-to-many user ↔ rôles |

**Alternative plus simple au début** : un enum `role` sur `User` + mapping hardcodé `ROLE → [permissions]` en Python. Moins flexible, plus rapide à livrer.

Fichiers à toucher : `auth_app/app/db/models.py`, puis schemas Pydantic.

---

### 2. Introduire des migrations

Aujourd’hui le projet utilise `Base.metadata.create_all` sans Alembic. Avant d’ajouter des tables, mettre **Alembic** en place pour ne pas casser la prod / les données existantes.

---

### 3. Seed des rôles / permissions

Au démarrage ou via un script :

1. Créer les permissions (`jobs:read`, `jobs:classify`, `users:manage`, …)
2. Créer les rôles
3. Lier rôles ↔ permissions
4. À l’inscription : assigner un rôle par défaut (ex. `viewer`)

---

### 4. Enrichir l’utilisateur et les tokens (optionnel)

- Charger les rôles (et éventuellement les permissions) avec le user
- Exposer rôles / permissions dans `GET /auth/me`
- **Option A** : mettre `roles` / `permissions` dans le JWT access → checks rapides, mais invalidation lente si on change un rôle
- **Option B** (souvent mieux) : JWT = identité seulement ; charger permissions depuis la DB dans la dépendance → plus à jour

Avec des access tokens très courts (1 min), l’option A est acceptable ; avec des TTL plus longs, préférer B ou un mix (rôles dans le JWT + rechargement si besoin).

---

### 5. Ajouter des gardes d’autorisation

Sur le modèle de `get_current_active_user` dans `auth_app/app/api/auth.py` :

```python
def require_permission(permission: str):
    def dependency(user = Depends(get_current_active_user)):
        if permission not in user_permissions(user):
            raise HTTPException(403, "Permission refusée")
        return user
    return dependency
```

Usage :

```python
@router.post("/classify")
def classify(..., user=Depends(require_permission("jobs:classify"))):
    ...
```

On peut aussi faire `require_roles("admin", "analyst")` si l’on préfère contrôler par rôle plutôt que par action.

---

### 6. API d’administration des rôles

Routes réservées (permission `users:manage` ou rôle `admin`) :

- Lister / créer / modifier rôles et permissions
- Assigner / retirer un rôle à un utilisateur
- (Optionnel) ne pas permettre de s’enlever soi-même le dernier admin

CRUD à ajouter à côté de `auth_app/app/crud/user.py`.

---

### 7. Protéger les endpoints métier

Pour chaque route sensible, déclarer l’action requise. Pas de rôle « magique » dispersé dans le code métier : une permission claire par action (`create`, `read`, `update`, `delete`, `classify`, …).

---

### 8. Tests et règles de sécurité

- User sans rôle → 403 sur les routes protégées
- User avec le bon rôle → 200
- Changement de rôle : vérifier le comportement (immédiat si DB, ou au prochain access token si JWT)
- Ne jamais faire confiance au client pour envoyer « je suis admin »

---

## Ordre de mise en œuvre suggéré

1. Tables + relations + migration  
2. Seed rôles/permissions + rôle défaut à l’inscription (`register`)  
3. Helper `user_permissions(user)` + `require_permission`  
4. Étendre `/auth/me`  
5. Routes admin d’assignation  
6. Appliquer les permissions sur les futures APIs (jobs, etc.)

---

## Principes à retenir

- **Rôles** = groupes d’utilisateurs  
- **Permissions** = actions permises  
- Le contrôle se fait avec une dépendance FastAPI du type `require_permission("...")`, pas seulement avec « être connecté »

---

## Critères de done (proposition)

- [ ] Modèle DB rôles / permissions (ou enum + mapping) en place  
- [ ] Migrations Alembic opérationnelles  
- [ ] Seed initial + rôle par défaut à l’inscription  
- [ ] `require_permission` (et/ou `require_roles`) utilisable sur les routes  
- [ ] `/auth/me` expose les rôles (et éventuellement les permissions)  
- [ ] Au moins une route admin pour assigner un rôle  
- [ ] Tests couvrant 403 / 200 selon les permissions  
