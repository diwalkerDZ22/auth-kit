"""Cookie httpOnly du refresh token et protection CSRF (voir docs/Sprint6-Frontend.md)."""
from fastapi import Request, Response

from auth_kit.config import AuthSettings
from auth_kit.errors import ApiError

# À autoriser dans le CORS de l'application si le frontend est sur une autre origine
CSRF_HEADER = "X-CSRF-Protection"


def _cookie_options(settings: AuthSettings) -> dict:
    return {
        "key": settings.refresh_cookie_name,
        "path": settings.refresh_cookie_path,
        "httponly": True,   # illisible en JavaScript : une faille XSS ne peut pas voler la session
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }


def set_refresh_cookie(settings: AuthSettings, response: Response, refresh_token: str) -> None:
    response.set_cookie(
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        **_cookie_options(settings),
    )


def clear_refresh_cookie(settings: AuthSettings, response: Response) -> None:
    response.delete_cookie(**_cookie_options(settings))


def clear_cookie_headers(settings: AuthSettings) -> dict:
    """Header Set-Cookie qui efface le cookie, à joindre à une ApiError."""
    response = Response()
    clear_refresh_cookie(settings, response)
    return {"set-cookie": response.headers["set-cookie"]}


def read_refresh_cookie(settings: AuthSettings, request: Request) -> str | None:
    return request.cookies.get(settings.refresh_cookie_name)


def require_csrf(request: Request) -> None:
    """Dépendance des routes qui lisent le cookie.

    Un autre site ne peut pas ajouter ce header sans requête preflight CORS,
    refusée puisque son origine n'est pas autorisée.
    """
    if request.headers.get(CSRF_HEADER) != "1":
        raise ApiError("csrf_missing")
