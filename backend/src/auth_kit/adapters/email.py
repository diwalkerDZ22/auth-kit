"""Implémentations de EmailSender : Resend, console (dev), mémoire (tests)."""
import logging

from auth_kit.ports import EmailMessage

logger = logging.getLogger(__name__)


class ResendEmailSender:
    """Envoi par Resend (pip install auth-kit[resend])."""

    def __init__(self, api_key: str, sender: str):
        """sender : "Nom <adresse@domaine>"."""
        import resend   # dépendance optionnelle

        if not api_key.strip():
            raise ValueError("ResendEmailSender : api_key vide")
        self._resend = resend
        self._api_key = api_key
        self.sender = sender

    def send(self, message: EmailMessage) -> bool:
        # Le SDK Resend lit une clé globale : on la (re)pose avant chaque envoi
        self._resend.api_key = self._api_key
        try:
            self._resend.Emails.send({
                "from": self.sender,
                "to": [message.to],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            })
            return True
        except Exception:
            logger.exception("Échec d'envoi d'email (purpose=%s)", message.purpose)
            return False


class ConsoleEmailSender:
    """DEV UNIQUEMENT : écrit le mail dans les logs, liens compris (seule exception à « pas de token dans les logs »)."""

    def send(self, message: EmailMessage) -> bool:
        logger.warning("[email console] %s | %s", message.subject, message.text.replace("\n", " | "))
        return True


class MemoryEmailSender:
    """Garde les mails en mémoire (tests). fail=True simule une panne du prestataire."""

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []
        self.fail = False

    def send(self, message: EmailMessage) -> bool:
        if self.fail:
            return False
        self.outbox.append(message)
        return True
