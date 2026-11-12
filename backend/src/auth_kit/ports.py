"""Interfaces vers l'extérieur. Le kit ne dépend que de ces contrats ; les implémentations
fournies sont dans auth_kit.adapters, et un projet peut brancher les siennes.
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str
    purpose: str   # "signup", "login", "reset", "account_exists" : pour les logs et les tests


@runtime_checkable
class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> bool:
        """Envoie le mail. False (sans exception) si l'envoi a échoué."""
        ...


@runtime_checkable
class RateLimiter(Protocol):
    enabled: bool

    def hit(self, limit: str, *keys: str) -> bool:
        """Compte un essai. False si la limite était déjà atteinte."""
        ...

    def test(self, limit: str, *keys: str) -> bool:
        """True s'il reste au moins un essai, sans en consommer."""
        ...

    def reset(self) -> None:
        ...


@runtime_checkable
class BreachChecker(Protocol):
    def is_breached(self, password: str) -> bool:
        """True si le mot de passe figure dans une fuite connue."""
        ...
