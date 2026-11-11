import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.email import send_verification_email
from app.core.errors import ApiError
from app.core.limiter import limiter
from app.core.verification import create_verification_link, hash_token
from app.crud.user import create_user, get_user_by_email, get_user_by_username
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import UserCreate, UserOut, VerifyRequest,ResendRequest


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
      document.getElementById("msg").textContent = data.message || "Réponse inattendue.";
    };
  </script>
</body></html>"""


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/15minutes")
def register(
    request: Request,
    user_in: UserCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if get_user_by_username(db, user_in.username):
        raise ApiError("username_taken")
    if get_user_by_email(db, user_in.email):
        raise ApiError("email_taken")

    try:
        user = create_user(db, user_in)
    except IntegrityError:
        db.rollback()
        raise ApiError("account_exists")

    link = create_verification_link(db, user, "signup")
    background.add_task(send_verification_email, user.email, link, "signup")
    logger.info("Inscription de %s (id=%s), email de vérification programmé", user.username, user.id)
    return user

@router.post("/verify")
@limiter.limit("10/15minutes")
def verify(request: Request, payload: VerifyRequest, db: Session = Depends(get_db)):
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
        logger.info("Lien de vérification invalide ou expiré")
        raise ApiError("invalid_link")

    user = verification.user
    verification.used_at = now  # lien à usage unique

    if verification.purpose == "signup":
        user.is_verified = True
        db.commit()
        logger.info("Email vérifié pour %s", user.username)
        return {"purpose": "signup", "message": "Email vérifié, vous pouvez vous connecter."}

    # purpose == "login" : on approuve seulement, aucun token émis ici
    if not user.is_verified or user.disabled:
        db.commit()  # le lien reste consommé
        raise ApiError("account_not_allowed")

    verification.approved_at = now
    db.commit()
    logger.info("Connexion approuvée par email pour %s", user.username)
    return {
        "purpose": "login",
        "message": "Connexion approuvée. Vous pouvez retourner sur la page de connexion.",
    }

@router.get("/verify", include_in_schema=False, response_class=HTMLResponse)
def verify_page():
    return VERIFY_PAGE

@router.post("/resend-verification")
@limiter.limit("3/15minutes")
def resend_verification(
    request: Request,
    payload: ResendRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)

    if user and not user.is_verified:
        last = (
            db.query(EmailVerification)
            .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == "signup")
            .order_by(EmailVerification.created_at.desc())
            .first()
        )
        if not last or datetime.now(timezone.utc) - last.created_at > timedelta(minutes=2):
            link = create_verification_link(db, user, "signup")
            background.add_task(send_verification_email, user.email, link, "signup")
            logger.info("Email de vérification renvoyé à %s", user.username)

    # Même réponse dans tous les cas : ne révèle pas si le compte existe
    return {"message": "Si un compte non vérifié existe pour cette adresse, un email a été envoyé."}
