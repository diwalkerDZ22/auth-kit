"""Connexion : mot de passe, lien email (approuver / refuser), récupération des tokens."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.errors import ApiError
from auth_kit.http.deps import AuthDependencies, client_info
from auth_kit.http.responses import session_response
from auth_kit.http.schemas import (
    AccessToken, ClaimRequest, LoginEmailSent, LoginPending, MessageOut, TokenRequest, VerifyOut,
)
from auth_kit.services import login as service
from auth_kit.services.sessions import open_session

_VERIFY_MESSAGES = {
    "signup": "Email vérifié, vous pouvez vous connecter.",
    "login": "Connexion approuvée. Vous pouvez retourner sur la page de connexion.",
}

_VERIFY_TEST_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Vérification</title></head>
<body style="font-family:sans-serif;max-width:420px;margin:60px auto">
  <h2>Confirmer votre email</h2>
  <button id="btn">Confirmer</button>
  <p id="msg"></p>
  <script>
    const token = new URLSearchParams(location.search).get("token");
    history.replaceState(null, "", location.pathname);
    document.getElementById("btn").onclick = async () => {
      const r = await fetch(location.pathname, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({token}),
      });
      const data = await r.json();
      document.getElementById("msg").textContent = data.message || "Réponse inattendue.";
    };
  </script>
</body></html>"""


def build_login_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["connexion"])
    settings = ctx.settings

    @router.post(
        "/token",
        response_model=AccessToken,
        responses={202: {"model": LoginEmailSent, "description": "Lien de connexion envoyé par email"}},
        dependencies=[Depends(deps.rate_limit("login"))],
    )
    def login(
        request: Request,
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(deps.get_db),
    ):
        user = service.check_password(db, ctx, form_data.username, form_data.password)
        client = client_info(request)
        if not settings.login_email_required:   # mode dev : pas d'étape email (Swagger)
            return session_response(settings, response, open_session(db, ctx, user, client))

        started = service.start_email_login(db, ctx, user, client)
        body = LoginEmailSent(
            code="login_email_sent",
            attempt_id=started.attempt_id,
            message="Un lien de connexion vient d'être envoyé à votre adresse email.",
        )
        return JSONResponse(status_code=202, content=body.model_dump())

    @router.post(
        "/login/claim",
        response_model=AccessToken,
        responses={202: {"model": LoginPending, "description": "Lien pas encore cliqué"}},
        dependencies=[Depends(deps.rate_limit("claim"))],
    )
    def claim_login(request: Request, response: Response, payload: ClaimRequest, db: Session = Depends(deps.get_db)):
        user = service.claim(db, ctx, payload.attempt_id)
        if user is None:
            body = LoginPending(code="login_pending", message="En attente de la confirmation par email.")
            return JSONResponse(status_code=202, content=body.model_dump())
        return session_response(settings, response, open_session(db, ctx, user, client_info(request)))

    @router.post("/verify", response_model=VerifyOut, dependencies=[Depends(deps.rate_limit("verify"))])
    def verify(payload: TokenRequest, db: Session = Depends(deps.get_db)):
        """Clic sur un lien signup (active le compte) ou login (approuve la connexion)."""
        purpose = service.confirm_link(db, payload.token)
        return VerifyOut(purpose=purpose, message=_VERIFY_MESSAGES[purpose])

    @router.get("/verify", include_in_schema=False, response_class=HTMLResponse)
    def verify_test_page():
        # Page de test sans frontend : désactivée par défaut (verify_test_page=True en dev)
        if not settings.verify_test_page:
            raise ApiError("not_found")
        return _VERIFY_TEST_PAGE

    @router.post("/login/deny", response_model=MessageOut, dependencies=[Depends(deps.rate_limit("deny"))])
    def deny_login(payload: TokenRequest, db: Session = Depends(deps.get_db)):
        """« Ce n'est pas moi » : annule la demande de connexion du lien."""
        service.deny(db, payload.token)
        return MessageOut(message=(
            "Connexion refusée. Quelqu'un connaît votre mot de passe : changez-le dès maintenant "
            "(« Mot de passe oublié » sur la page de connexion)."
        ))

    return router
