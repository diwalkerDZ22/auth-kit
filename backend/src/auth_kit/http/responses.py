from fastapi import Response

from auth_kit.config import AuthSettings
from auth_kit.http.cookies import set_refresh_cookie
from auth_kit.services.sessions import IssuedSession


def session_response(settings: AuthSettings, response: Response, issued: IssuedSession) -> dict:
    """Access token dans le corps, refresh token en cookie httpOnly (s'il a changé)."""
    if issued.refresh_token is not None:
        set_refresh_cookie(settings, response, issued.refresh_token)
    return issued.access
