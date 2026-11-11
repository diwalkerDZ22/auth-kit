"""Règles de mot de passe et de username (voir docs/Sprint5-Auth-complete.md).

Recommandations NIST : la longueur compte plus que la composition ; on refuse
les mots de passe trop courants plutôt que d'imposer majuscule / chiffre / symbole.
"""
import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72   # bcrypt ignore tout ce qui dépasse 72 octets

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")

# Extrait des mots de passe les plus fréquents dans les fuites publiques
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "motdepasse", "12345678", "123456789",
    "1234567890", "qwertyuiop", "azertyuiop", "azerty123", "qwerty123", "iloveyou",
    "sunshine", "princess", "football", "baseball", "welcome1", "admin123",
    "letmein1", "11111111", "00000000", "abcd1234", "abc12345", "trustno1",
    "superman", "dragon123", "monkey123", "soleil123", "bonjour1", "doudou123",
}


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
