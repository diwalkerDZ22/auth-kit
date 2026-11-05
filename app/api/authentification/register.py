import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.email import send_verification_email
from app.core.verification import create_verification_link, hash_token
from app.crud.user import create_user, get_user_by_email, get_user_by_username
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import UserCreate, UserOut, VerifyRequest

from app.api.authentification.login import issue_tokens


router = APIRouter()
logger = logging.getLogger(__name__)

VERIFY_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Vérification</title></head>
<body style="font-family:sans-serif;max-width:420px;margin:60px auto">
  <h2>Confirmer votre email</h2>
  <button id="btn">Confirmer</button>
  <p id="msg"></p>
  <script>
    const token = new URLSearchParams(location.search).get("token");
    history.replaceState(null, "", location.pathname);
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
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered",
        )

    link = create_verification_link(db, user, "signup")
    background.add_task(send_verification_email, user.email, link, "signup")
    return user


@router.post("/verify")
def verify(payload: VerifyRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.token_hash == hash_token(payload.token),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
        )
        .with_for_update()
        .first()
    )
    if not verification:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")

    user = verification.user
    verification.used_at = now

    if verification.purpose == "signup":
        user.is_verified = True
        db.commit()
        return {"detail": "Email vérifié, vous pouvez vous connecter."}

    if not user.is_verified or user.disabled:
        db.commit()
        raise HTTPException(status_code=403, detail="Compte non vérifié ou désactivé")

    db.commit()
    return issue_tokens(db, user)


@router.get("/verify", include_in_schema=False, response_class=HTMLResponse)
def verify_page():
    return VERIFY_PAGE
