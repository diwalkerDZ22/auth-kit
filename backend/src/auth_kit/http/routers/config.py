"""GET /config : ce que le frontend doit savoir pour s'adapter (fonctionnalités, règles)."""
from fastapi import APIRouter

from auth_kit.context import KitContext
from auth_kit.http.schemas import AuthConfigOut, PasswordRules
from auth_kit.passwords import PASSWORD_MAX_BYTES, PASSWORD_MIN_LENGTH, USERNAME_REGEX


def build_config_router(ctx: KitContext, features: frozenset[str]) -> APIRouter:
    router = APIRouter(tags=["configuration"])
    s = ctx.settings
    body = AuthConfigOut(
        features=sorted(features),
        login_email_required=s.login_email_required,
        access_token_expire_seconds=s.access_token_expire_minutes * 60,
        login_link_expire_seconds=s.login_token_expire_minutes * 60,
        password=PasswordRules(
            min_length=PASSWORD_MIN_LENGTH,
            max_bytes=PASSWORD_MAX_BYTES,
            breach_check=ctx.breach_checker is not None,
        ),
        username_pattern=USERNAME_REGEX,
    )

    @router.get("/config", response_model=AuthConfigOut)
    def auth_config():
        return body

    return router
