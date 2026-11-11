import sys

from app.db.base import SessionLocal
from app.db.models import User, EmailVerification
from app.core.verification import create_verification_link, hash_token

db = SessionLocal()
try:
    if len(sys.argv) < 2:
        names = [row[0] for row in db.query(User.username).all()]
        print("Usage : python -m scripts.check_link <username>")
        print("Comptes existants :", names)
        sys.exit(1)

    user = db.query(User).filter(User.username == sys.argv[1]).first()
    if not user:
        print(f"Aucun utilisateur '{sys.argv[1]}'.")
        sys.exit(1)

    link = create_verification_link(db, user, "login", "mon-secret-de-test")

    row = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == "login")
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    print("attempt_hash correct :", row.attempt_hash == hash_token("mon-secret-de-test"))
    print("expire dans :", row.expires_at - row.created_at)
    print("lien :", link.split("?")[0] + "?token=...")  # le token n'est pas affiché
finally:
    db.close()