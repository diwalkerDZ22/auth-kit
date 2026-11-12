"""Règles de mot de passe et de username (voir docs/Sprint5-Auth-complete.md).

Recommandations NIST : la longueur compte plus que la composition ; on refuse
les mots de passe trop courants plutôt que d'imposer majuscule / chiffre / symbole.

password_problem() : règles statiques (utilisables dans un schéma Pydantic).
new_password_error() : règles statiques + fuites connues (BreachChecker du kit).
"""
import re

from auth_kit.context import KitContext
from auth_kit.errors import ApiError

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72   # bcrypt ignore tout ce qui dépasse 72 octets

USERNAME_REGEX = r"^[A-Za-z0-9_.-]{3,30}$"
USERNAME_PATTERN = re.compile(USERNAME_REGEX)

# Extrait des mots de passe les plus fréquents dans les fuites publiques.
# Filet hors ligne : un BreachChecker (Have I Been Pwned) couvre des centaines de millions de fuites.
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "motdepasse", "12345678", "123456789",
    "1234567890", "qwertyuiop", "azertyuiop", "azerty123", "qwerty123", "iloveyou",
    "sunshine", "princess", "football", "baseball", "welcome1", "admin123",
    "letmein1", "11111111", "00000000", "abcd1234", "abc12345", "trustno1",
    "superman", "dragon123", "monkey123", "soleil123", "bonjour1", "doudou123",
}

BREACHED_MESSAGE = "Ce mot de passe apparaît dans des fuites de données connues, choisissez-en un autre."


def password_problem(password: str, username: str | None = None, email: str | None = None) -> str | None:
    """Renvoie le message d'erreur à afficher, ou None si le mot de passe est accepté."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Le mot de passe ne doit pas dépasser {PASSWORD_MAX_BYTES} octets."
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return "Ce mot de passe est trop courant, choisissez-en un autre."
    if username and lowered == username.lower():
        return "Le mot de passe doit être différent du nom d'utilisateur."
    if email and (lowered == email.lower() or lowered == email.split("@")[0].lower()):
        return "Le mot de passe doit être différent de l'adresse email."
    return None


def username_problem(username: str) -> str | None:
    if not USERNAME_PATTERN.match(username):
        return "De 3 à 30 caractères : lettres, chiffres, « _ », « . » ou « - »."
    return None


def full_password_problem(ctx: KitContext, password: str, username: str | None, email: str | None) -> str | None:
    problem = password_problem(password, username, email)
    if problem is None and ctx.breach_checker is not None and ctx.breach_checker.is_breached(password):
        return BREACHED_MESSAGE
    return problem


def new_password_error(ctx: KitContext, username: str, email: str, password: str, field: str) -> ApiError | None:
    """Erreur 422 au même format que la validation Pydantic, ou None si le mot de passe convient."""
    problem = full_password_problem(ctx, password, username, email)
    if problem:
        return ApiError("validation_error", fields={field: problem})
    return None
