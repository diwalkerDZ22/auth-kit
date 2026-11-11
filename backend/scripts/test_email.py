"""Teste l'envoi d'email de vérification.

Usage (depuis backend/) :
    python -m scripts.test_email ton.email@exemple.com
    python -m scripts.test_email ton.email@exemple.com --purpose login
    python -m scripts.test_email ton.email@exemple.com --purpose reset
"""
import argparse
import logging
import secrets
import sys

from app.core.config import settings
from app.core.email import send_verification_email  


def main() -> int:
    parser = argparse.ArgumentParser(description="Test d'envoi d'email de vérification")
    parser.add_argument("to", help="adresse destinataire")
    parser.add_argument("--purpose", choices=["signup", "login", "reset"], default="signup")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)  # affiche la stack trace si l'envoi échoue

    fake_token = secrets.token_urlsafe(32)
    base_url = settings.FRONTEND_RESET_URL if args.purpose == "reset" else settings.FRONTEND_VERIFY_URL
    verify_url = f"{base_url}?token={fake_token}"

    print(f"Expéditeur   : {settings.mail_sender_name} <{settings.MAIL_FROM}>")
    print(f"Destinataire : {args.to}")
    print(f"Purpose      : {args.purpose}")
    print(f"Lien         : {verify_url}")
    print("Envoi...")

    result = send_verification_email(args.to, verify_url, args.purpose)

    # Ta version d'origine renvoie None (pas d'exception = succès) ;
    # la version avec try/except renvoie True/False.
    if result is False:
        print("ÉCHEC : voir l'erreur ci-dessus.")
        return 1

    print("OK : email envoyé. Vérifie ta boîte de réception (et les spams).")
    return 0


if __name__ == "__main__":
    sys.exit(main())