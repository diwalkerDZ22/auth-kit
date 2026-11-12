"""Hash des mots de passe (bcrypt) et access tokens (JWT, PyJWT)."""
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt

from auth_kit.config import AuthSettings

BCRYPT_MAX_BYTES = 72   # bcrypt refuse (v5) ou ignore (v4) ce qui dépasse 72 octets


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password = plain_password.encode("utf-8")
    if len(password) > BCRYPT_MAX_BYTES:
        # Impossible à l'inscription (règles de mot de passe) : ne peut correspondre à aucun compte
        return False
    try:
        return bcrypt.checkpw(password, hashed_password.encode("ascii"))
    except ValueError:   # hash corrompu ou dans un autre format
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    # Calculé au premier besoin (pas à l'import) : hash d'un mot de passe aléatoire
    return get_password_hash(secrets.token_urlsafe(16))


def burn_password_check() -> None:
    """Même coût qu'une vraie vérification : le temps de réponse ne révèle pas si le compte existe."""
    verify_password("x", _dummy_hash())


def create_access_token(settings: AuthSettings, claims: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
        # identifiant unique : deux tokens émis dans la même seconde restent différents
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(settings: AuthSettings, token: str) -> dict | None:
    """Claims d'un access token valide, ou None (signature, expiration, type ou claims manquants)."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub", "sid", "type"]},
        )
    except jwt.PyJWTError:
        return None
    return payload if payload.get("type") == "access" else None
