import html
import logging

import resend
from app.core.config import settings

logger = logging.getLogger(__name__)
resend.api_key = settings.resend_api_key

def send_verification_email(to: str, verify_url: str, purpose: str) -> bool:
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
            "from": f"{settings.mail_from_name} <{settings.mail_from}>",
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