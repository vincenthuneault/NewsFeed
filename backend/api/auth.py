"""Routes /api/auth/login et /api/auth/logout."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from backend.auth import check_password, is_authenticated

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not check_password(password):
        return jsonify({"error": True, "message": "Mot de passe incorrect", "code": "UNAUTHORIZED"}), 401

    session["authenticated"] = True
    session.permanent = True
    return jsonify({"success": True})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/auth/status", methods=["GET"])
def status():
    return jsonify({"authenticated": is_authenticated()})
