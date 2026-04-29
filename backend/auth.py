"""Auth — mot de passe unique + cookie de session Flask."""

from __future__ import annotations

import os
from functools import wraps

from flask import jsonify, session


def _get_password() -> str:
    """Lit le mot de passe depuis l'environnement ou la config."""
    return os.getenv("APP_PASSWORD", "")


def is_authenticated() -> bool:
    return bool(session.get("authenticated"))


def require_auth(f):
    """Décorateur — retourne 401 si non authentifié."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _get_password() and not is_authenticated():
            return jsonify({"error": True, "message": "Non autorisé", "code": "UNAUTHORIZED"}), 401
        return f(*args, **kwargs)
    return decorated


def check_password(password: str) -> bool:
    expected = _get_password()
    if not expected:
        return True  # Mode sans auth (dev)
    return password == expected
