"""Cookie httpOnly du refresh token et protection CSRF (voir docs/Sprint6-Frontend.md)."""
from fastapi import Request, Response

from app.core.config import settings
from app.core.errors import ApiError

CSRF_HEADER = "X-CSRF-Protection"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,   # illisible en JavaScript : une faille XSS ne peut pas voler la session
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_cookie_headers() -> dict:
    """Header Set-Cookie qui efface le cookie, à joindre à une ApiError."""
    response = Response()
    clear_refresh_cookie(response)
    return {"set-cookie": response.headers["set-cookie"]}


def read_refresh_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.REFRESH_COOKIE_NAME)


def require_csrf(request: Request) -> None:
    """Dépendance des routes qui lisent le cookie.

    Un autre site ne peut pas ajouter ce header sans requête preflight CORS,
    refusée puisque son origine n'est pas autorisée.
    """
    if request.headers.get(CSRF_HEADER) != "1":
        raise ApiError("csrf_missing")
