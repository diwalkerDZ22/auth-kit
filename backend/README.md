# auth-kit (backend)

Authentification et autorisation pour FastAPI, en bibliothèque : connexion en deux étapes par email,
sessions par appareil, rôles et permissions, administration des comptes.

```bash
pip install "auth-kit[resend,postgres] @ git+https://github.com/<compte>/auth-kit.git#subdirectory=backend"
```

```python
from fastapi import Depends, FastAPI
from sqlalchemy.orm import sessionmaker

from auth_kit import AuthKit, AuthSettings
from auth_kit.adapters import ResendEmailSender
from auth_kit.db import create_engine_from_url, session_dependency
from auth_kit.models import User

engine = create_engine_from_url("postgresql://...")
get_db = session_dependency(sessionmaker(bind=engine))

kit = AuthKit(
    settings=AuthSettings(),                      # variables AUTH_* (AUTH_SECRET_KEY obligatoire)
    get_db=get_db,
    email=ResendEmailSender(api_key="re_...", sender="Mon app <no-reply@mon-app.fr>"),
)
app = FastAPI()
kit.install(app)                                  # /auth/* et /admin/*

@app.get("/jobs")
def jobs(user: User = Depends(kit.current_user)): ...
```

Guide complet (fonctionnalités, extension, migrations, déploiement) : `docs/Bibliotheque.md` à la racine du dépôt.
Application de démo : `example/main.py` (`python -m uvicorn --factory example.main:create_app --reload`).
