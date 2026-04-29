"""Routes GET/PUT /api/settings — préférences utilisateur."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

settings_bp = Blueprint("settings", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SETTINGS_FILE = PROJECT_ROOT / "data" / "settings.json"

_DEFAULTS: dict = {
    "max_feed_items": 30,
    "category_weights": {},
    "notifications_enabled": False,
}


def _load() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(_load())


@settings_bp.route("/settings", methods=["PUT"])
def put_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": True, "message": "Body JSON invalide", "code": "BAD_REQUEST"}), 400

    current = _load()

    # Valider et fusionner les clés connues
    if "max_feed_items" in data:
        val = data["max_feed_items"]
        if not isinstance(val, int) or not (1 <= val <= 100):
            return jsonify({"error": True, "message": "max_feed_items : entier 1-100", "code": "BAD_REQUEST"}), 400
        current["max_feed_items"] = val

    if "category_weights" in data:
        weights = data["category_weights"]
        if not isinstance(weights, dict):
            return jsonify({"error": True, "message": "category_weights : dict attendu", "code": "BAD_REQUEST"}), 400
        for k, v in weights.items():
            if not isinstance(v, (int, float)) or not (0.0 <= v <= 3.0):
                return jsonify({"error": True, "message": f"Poids invalide pour '{k}' (0.0–3.0)", "code": "BAD_REQUEST"}), 400
        current["category_weights"] = {**current["category_weights"], **weights}

    if "notifications_enabled" in data:
        current["notifications_enabled"] = bool(data["notifications_enabled"])

    _save(current)
    return jsonify(current)
