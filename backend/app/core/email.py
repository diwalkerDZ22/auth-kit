import html
import logging

import resend
from app.core.config import settings

logger = logging.getLogger(__name__)
resend.api_key = settings.RESEND_API_KEY

# purpose -> (sujet, phrase d'introduction)
_TEMPLATES = {
    "signup": ("Confirmez votre adresse email", "Cliquez pour activer votre compte :"),
    "login": ("Confirmez cette connexion", "Une connexion a été demandée. Cliquez pour continuer :"),
    "reset": (
        "Réinitialisez votre mot de passe",
        "Une réinitialisation du mot de passe a été demandée. Cliquez pour choisir un nouveau mot de passe :",
    ),
}


def send_verification_email(to: str, verify_url: str, purpose: str) -> bool:
    if not settings.RESEND_API_KEY.strip():
        logger.error("Envoi impossible: RESEND_API_KEY n'est pas configurée dans le fichier .env")
        return False

    subject, intro = _TEMPLATES.get(purpose, _TEMPLATES["signup"])
    safe_url = html.escape(verify_url, quote=True)
    footer = "Si vous n’êtes pas à l’origine de cette demande, ignorez ce mail."

    try:
        resend.Emails.send({
            "from": f"{settings.mail_sender_name} <{settings.MAIL_FROM}>",
            "to": [to],
            "subject": subject,
            "html": (
                f"<p>{intro}</p>"
                f'<p><a href="{safe_url}">{safe_url}</a></p>'
                f"<p>{footer}</p>"
            ),
            "text": f"{intro}\n{verify_url}\n\n{footer}",  # version texte, meilleure délivrabilité
        })
        return True
    except Exception:
        logger.exception("Échec d'envoi d'email de vérification (purpose=%s)", purpose)
        return False
