import html
import logging

import resend
from app.core.config import settings

logger = logging.getLogger(__name__)
resend.api_key = settings.RESEND_API_KEY

def send_verification_email(to: str, verify_url: str, purpose: str) -> bool:
    if not settings.RESEND_API_KEY.strip():
        logger.error("Envoi impossible: RESEND_API_KEY n'est pas configurée dans le fichier .env")
        return False

    if purpose == "login":
        subject = "Confirmez cette connexion"
        intro = "Une connexion a été demandée. Cliquez pour continuer :"
    else:
        subject = "Confirmez votre adresse email"
        intro = "Cliquez pour activer votre compte :"

    safe_url = html.escape(verify_url, quote=True)
    footer = "Si vous n’êtes pas à l’origine de cette demande, ignorez ce mail."

    try:
        resend.Emails.send({
            "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
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