"""Ligne de commande `auth-kit`.

    auth-kit seed-roles                       # rôles par défaut du kit (user, admin)
    auth-kit cleanup [--days 7]               # liens et sessions périmés (à planifier)
    auth-kit test-email moi@exemple.fr [--purpose login] [--backend console|resend]
    auth-kit migrations-path                  # dossier à ajouter à version_locations

Base : --database-url, ou DATABASE_URL (variable d'environnement ou .env du dossier courant).
Rôles propres au projet : appeler kit.seed_roles(db) depuis le code du projet.
"""
import argparse
import logging
import os
import secrets
import sys

from sqlalchemy.orm import sessionmaker

from auth_kit.context import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from auth_kit.db import create_engine_from_url
from auth_kit.migrations import VERSIONS_PATH
from auth_kit.templates import EmailTemplates, render_link_email


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(".env")


def _session(database_url: str | None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("URL de base manquante : --database-url ou variable DATABASE_URL")
    engine = create_engine_from_url(url, sslmode=os.environ.get("DATABASE_SSLMODE", "require"))
    return sessionmaker(bind=engine)()


def _seed_roles(args) -> int:
    from auth_kit.services.roles import seed_roles

    db = _session(args.database_url)
    try:
        seed_roles(db, DEFAULT_ROLES, DEFAULT_PERMISSIONS)
    finally:
        db.close()
    for name, spec in DEFAULT_ROLES.items():
        print(f"  {name}: {', '.join(spec.permissions) or '(aucune permission)'}")
    return 0


def _cleanup(args) -> int:
    from auth_kit.services.maintenance import cleanup

    db = _session(args.database_url)
    try:
        links, sessions = cleanup(db, args.days)
    finally:
        db.close()
    print(f"{links} lien(s) email et {sessions} session(s) supprimés.")
    return 0


def _test_email(args) -> int:
    from auth_kit.adapters.email import ConsoleEmailSender, ResendEmailSender

    if args.backend == "console":
        sender = ConsoleEmailSender()
    else:
        api_key = os.environ.get("RESEND_API_KEY", "")
        mail_from = os.environ.get("MAIL_FROM", "onboarding@resend.dev")
        if not api_key:
            sys.exit("RESEND_API_KEY manquante")
        sender = ResendEmailSender(api_key, f"{args.app_name} <{mail_from}>")

    url = f"http://localhost:5173/verify-email?token={secrets.token_urlsafe(32)}&type={args.purpose}"
    context = {"date": "maintenant", "ip": "127.0.0.1", "browser": "auth-kit test-email"} if args.purpose == "login" else None
    message = render_link_email(EmailTemplates(), args.app_name, args.to, url, args.purpose, context)
    print(f"Destinataire : {args.to}\nSujet        : {message.subject}\nEnvoi...")
    if not sender.send(message):
        print("ÉCHEC : voir l'erreur ci-dessus.")
        return 1
    print("OK : email envoyé. Vérifie ta boîte de réception (et les spams).")
    return 0


def _migrations_path(args) -> int:
    print(VERSIONS_PATH)
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="auth-kit", description="Outils d'auth-kit")
    parser.add_argument("--database-url", help="défaut : variable DATABASE_URL")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("seed-roles", help="crée / synchronise les rôles par défaut").set_defaults(run=_seed_roles)

    cleanup_cmd = commands.add_parser("cleanup", help="supprime les liens et sessions périmés")
    cleanup_cmd.add_argument("--days", type=int, default=7, help="jours d'historique conservés (défaut : 7)")
    cleanup_cmd.set_defaults(run=_cleanup)

    email_cmd = commands.add_parser("test-email", help="envoie un mail de test")
    email_cmd.add_argument("to")
    email_cmd.add_argument("--purpose", choices=["signup", "login", "reset"], default="signup")
    email_cmd.add_argument("--backend", choices=["console", "resend"], default="resend")
    email_cmd.add_argument("--app-name", default="auth-kit")
    email_cmd.set_defaults(run=_test_email)

    commands.add_parser("migrations-path", help="dossier des migrations du kit").set_defaults(run=_migrations_path)

    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
