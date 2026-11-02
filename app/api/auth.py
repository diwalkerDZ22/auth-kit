from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, create_refresh_token
from app.core.email import send_verification_email
from app.core.verification import create_verification_link
from app.crud.user import authenticate_user, create_user, get_user_by_username, get_user_by_email, save_refresh_token, revoke_refresh_token
from app.db.base import get_db
from app.schemas.user import Token, TokenData, UserCreate, UserOut, TokenPair, RefreshRequest, VerifyRequest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.verification import hash_token
from app.db.models import EmailVerification
from app.schemas.user import VerifyRequest  # le schéma avec le champ `token: str`

router = APIRouter()

bearer_scheme = HTTPBearer()


# --- Dependency : récupère le user connecté depuis le token ---

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user

6
def get_current_active_user(current_user=Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# --- Routes ---

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from app.core.email import send_verification_email
from app.core.verification import create_verification_link


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    user_in: UserCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if get_user_by_email(db, user_in.email.lower()):
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        user = create_user(db, user_in)
    except IntegrityError:  # deux inscriptions simultanées avec le même username/email
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already registered")

    link = create_verification_link(db, user, "signup")
    background.add_task(send_verification_email, user.email, link, "signup")

    return user


@router.post("/verify")
def verify(payload: VerifyRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    # 1-2. Hasher puis chercher une ligne valide
    v = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.token_hash == hash_token(payload.token),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
        )
        .with_for_update()
        .first()
    )
    if not v:
        raise HTTPException(400, "Lien invalide ou expiré")

    user = v.user

    # 3. Marquer comme utilisé
    v.used_at = now

    # 4. Signup : on active le compte, aucun JWT
    if v.purpose == "signup":
        user.is_verified = True
        db.commit()
        return {"detail": "Email vérifié, vous pouvez vous connecter."}

    # 5. Login : contrôle puis émission des tokens
    if not user.is_verified or user.disabled:
        db.commit()  # le token reste consommé
        raise HTTPException(403, "Compte non vérifié ou désactivé")

    access = create_access_token(user.username)
    refresh = create_refresh_token(user.username)
    user.refresh_token = refresh
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

VERIFY_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Vérification</title></head>
<body style="font-family:sans-serif;max-width:420px;margin:60px auto">
  <h2>Confirmer votre email</h2>
  <button id="btn">Confirmer</button>
  <p id="msg"></p>
  <script>
    const token = new URLSearchParams(location.search).get("token");
    history.replaceState(null, "", location.pathname);  // retire le token de la barre d'adresse
    document.getElementById("btn").onclick = async () => {
      const r = await fetch("/auth/verify", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({token}),
      });
      const data = await r.json();
      document.getElementById("msg").textContent = data.detail || "Connexion réussie.";
    };
  </script>
</body></html>"""


@router.get("/verify", include_in_schema=False)
def verify_page():
    return HTMLResponse(VERIFY_PAGE)

@router.post("/token", response_model=TokenPair)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    save_refresh_token(db, user.id, refresh_token)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenPair)
def refresh_access_token(body: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Invalid refresh token")
    
    payload = decode_access_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise credentials_exception
    
    username = payload.get("sub")
    user = get_user_by_username(db, username)
    
    if user is None or user.refresh_token != body.refresh_token:
        raise credentials_exception

    # Génère les deux nouveaux tokens
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh = create_refresh_token(data={"sub": user.username})
    
    # Écrase l'ancien refresh en DB
    save_refresh_token(db, user.id, new_refresh)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    revoke_refresh_token(db, current_user.id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_active_user)):
    return current_user