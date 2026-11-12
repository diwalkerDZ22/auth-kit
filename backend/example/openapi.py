"""Écrit le contrat OpenAPI de l'application de démo (source des types du frontend).

    cd backend
    python -m example.openapi ../frontend/packages/auth-kit/openapi.json
"""
import json
import os
import sys


def build_openapi() -> dict:
    # Réglages fixes : le contrat ne doit dépendre ni du .env ni de la machine
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("AUTH_SECRET_KEY", "openapi-only-0123456789abcdef0123456789")
    os.environ.setdefault("EMAIL_BACKEND", "console")
    from example.main import create_app

    return create_app(env_file=None).openapi()


def dump(schema: dict) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


if __name__ == "__main__":
    output = dump(build_openapi())
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
            f.write(output)
    else:
        sys.stdout.write(output)
