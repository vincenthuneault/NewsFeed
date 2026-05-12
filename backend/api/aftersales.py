"""Routes /api/aftersales — suivi ECR, MCA et investigations."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from core.models import (
    ECR,
    MCA,
    ECRStatusHistory,
    Investigation,
    MCAStatusHistory,
    get_session,
    init_db,
    seed_aftersales_data,
)

aftersales_bp = Blueprint("aftersales", __name__)

_ECR_STATUSES = {"a_transmettre", "en_cours", "corrige", "annule"}
_MCA_STATUSES = {"a_appliquer", "applique", "en_attente"}


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


def _ecr_to_dict(ecr: ECR) -> dict:
    return {
        "id": ecr.id,
        "ecr_number": ecr.ecr_number,
        "title": ecr.title,
        "status": ecr.status,
        "priority": ecr.priority,
        "severity": ecr.severity,
        "symptom": ecr.symptom,
        "root_cause": ecr.root_cause,
        "proposed_fix": ecr.proposed_fix,
        "created_at": ecr.created_at.isoformat(),
        "updated_at": ecr.updated_at.isoformat() if ecr.updated_at else None,
        "closed_at": ecr.closed_at.isoformat() if ecr.closed_at else None,
    }


def _mca_to_dict(mca: MCA) -> dict:
    return {
        "id": mca.id,
        "mca_number": mca.mca_number,
        "title": mca.title,
        "status": mca.status,
        "target_agent": mca.target_agent,
        "description": mca.description,
        "justification": mca.justification,
        "blocking_ecr_id": mca.blocking_ecr_id,
        "created_at": mca.created_at.isoformat(),
        "applied_at": mca.applied_at.isoformat() if mca.applied_at else None,
    }


def _investigation_to_dict(inv: Investigation) -> dict:
    return {
        "id": inv.id,
        "trigger_type": inv.trigger_type,
        "trigger_id": inv.trigger_id,
        "hypothesis": inv.hypothesis,
        "data_plan": inv.data_plan,
        "data_collected": inv.data_collected,
        "conclusion": inv.conclusion,
        "decision": inv.decision,
        "ecr_id": inv.ecr_id,
        "mca_id": inv.mca_id,
        "created_at": inv.created_at.isoformat(),
        "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
    }


# ── ECR ──────────────────────────────────────────────────────────────────────

@aftersales_bp.route("/aftersales/ecr", methods=["GET"])
def list_ecr():
    """Liste les ECRs. Paramètre optionnel : ?status=a_transmettre"""
    session = _get_session()
    try:
        q = session.query(ECR)
        status = request.args.get("status")
        if status:
            q = q.filter(ECR.status == status)
        ecrs = q.order_by(ECR.ecr_number).all()
        return jsonify({"ecr": [_ecr_to_dict(e) for e in ecrs], "total": len(ecrs)})
    finally:
        session.close()


@aftersales_bp.route("/aftersales/ecr", methods=["POST"])
def create_ecr():
    """Crée un nouvel ECR."""
    data = request.get_json(silent=True) or {}
    required = ("ecr_number", "title")
    for field in required:
        if not data.get(field):
            return jsonify({"error": True, "message": f"{field} requis"}), 400

    session = _get_session()
    try:
        if session.query(ECR).filter_by(ecr_number=data["ecr_number"]).first():
            return jsonify({"error": True, "message": "ecr_number déjà existant"}), 409

        ecr = ECR(
            ecr_number=data["ecr_number"],
            title=data["title"],
            status=data.get("status", "a_transmettre"),
            priority=data.get("priority", "normale"),
            severity=data.get("severity", "normale"),
            symptom=data.get("symptom"),
            root_cause=data.get("root_cause"),
            proposed_fix=data.get("proposed_fix"),
        )
        session.add(ecr)
        session.commit()
        return jsonify({"success": True, "ecr": _ecr_to_dict(ecr)}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


@aftersales_bp.route("/aftersales/ecr/<int:ecr_id>/status", methods=["PATCH"])
def update_ecr_status(ecr_id: int):
    """Met à jour le statut d'un ECR et enregistre l'historique.

    Body JSON : {"status": "en_cours", "note": "Transmis à l'arch prod le ..."}
    """
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    if new_status not in _ECR_STATUSES:
        return jsonify({"error": True, "message": f"Statut invalide. Valeurs : {_ECR_STATUSES}"}), 400

    session = _get_session()
    try:
        ecr = session.get(ECR, ecr_id)
        if not ecr:
            return jsonify({"error": True, "message": "ECR introuvable"}), 404

        history = ECRStatusHistory(
            ecr_id=ecr_id,
            old_status=ecr.status,
            new_status=new_status,
            note=data.get("note"),
        )
        session.add(history)
        ecr.status = new_status
        if new_status in ("corrige", "annule"):
            ecr.closed_at = datetime.now(timezone.utc)
        session.commit()
        return jsonify({"success": True, "ecr": _ecr_to_dict(ecr)})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


@aftersales_bp.route("/aftersales/ecr/<int:ecr_id>/history", methods=["GET"])
def ecr_history(ecr_id: int):
    """Retourne l'historique des changements de statut d'un ECR."""
    session = _get_session()
    try:
        ecr = session.get(ECR, ecr_id)
        if not ecr:
            return jsonify({"error": True, "message": "ECR introuvable"}), 404
        history = (
            session.query(ECRStatusHistory)
            .filter_by(ecr_id=ecr_id)
            .order_by(ECRStatusHistory.changed_at.asc())
            .all()
        )
        return jsonify({
            "ecr_number": ecr.ecr_number,
            "history": [
                {
                    "old_status": h.old_status,
                    "new_status": h.new_status,
                    "note": h.note,
                    "changed_at": h.changed_at.isoformat(),
                }
                for h in history
            ],
        })
    finally:
        session.close()


# ── MCA ──────────────────────────────────────────────────────────────────────

@aftersales_bp.route("/aftersales/mca", methods=["GET"])
def list_mca():
    """Liste les MCAs. Paramètre optionnel : ?status=a_appliquer"""
    session = _get_session()
    try:
        q = session.query(MCA)
        status = request.args.get("status")
        if status:
            q = q.filter(MCA.status == status)
        mcas = q.order_by(MCA.mca_number).all()
        return jsonify({"mca": [_mca_to_dict(m) for m in mcas], "total": len(mcas)})
    finally:
        session.close()


@aftersales_bp.route("/aftersales/mca", methods=["POST"])
def create_mca():
    """Crée un nouveau MCA."""
    data = request.get_json(silent=True) or {}
    for field in ("mca_number", "title"):
        if not data.get(field):
            return jsonify({"error": True, "message": f"{field} requis"}), 400

    session = _get_session()
    try:
        if session.query(MCA).filter_by(mca_number=data["mca_number"]).first():
            return jsonify({"error": True, "message": "mca_number déjà existant"}), 409

        mca = MCA(
            mca_number=data["mca_number"],
            title=data["title"],
            status=data.get("status", "a_appliquer"),
            target_agent=data.get("target_agent"),
            description=data.get("description"),
            justification=data.get("justification"),
            blocking_ecr_id=data.get("blocking_ecr_id"),
        )
        session.add(mca)
        session.commit()
        return jsonify({"success": True, "mca": _mca_to_dict(mca)}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


@aftersales_bp.route("/aftersales/mca/<int:mca_id>/status", methods=["PATCH"])
def update_mca_status(mca_id: int):
    """Met à jour le statut d'un MCA et enregistre l'historique."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    if new_status not in _MCA_STATUSES:
        return jsonify({"error": True, "message": f"Statut invalide. Valeurs : {_MCA_STATUSES}"}), 400

    session = _get_session()
    try:
        mca = session.get(MCA, mca_id)
        if not mca:
            return jsonify({"error": True, "message": "MCA introuvable"}), 404

        history = MCAStatusHistory(
            mca_id=mca_id,
            old_status=mca.status,
            new_status=new_status,
            note=data.get("note"),
        )
        session.add(history)
        mca.status = new_status
        if new_status == "applique":
            mca.applied_at = datetime.now(timezone.utc)
        session.commit()
        return jsonify({"success": True, "mca": _mca_to_dict(mca)})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


# ── Investigations ────────────────────────────────────────────────────────────

@aftersales_bp.route("/aftersales/investigations", methods=["GET"])
def list_investigations():
    """Liste les investigations. Paramètre optionnel : ?limit=20"""
    session = _get_session()
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
        investigations = (
            session.query(Investigation)
            .order_by(Investigation.created_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({
            "investigations": [_investigation_to_dict(i) for i in investigations],
            "total": len(investigations),
        })
    finally:
        session.close()


@aftersales_bp.route("/aftersales/investigations", methods=["POST"])
def create_investigation():
    """Crée un log d'investigation.

    Body JSON : {trigger_type, trigger_id?, hypothesis?, data_plan?,
                 data_collected?, conclusion?, decision?, ecr_id?, mca_id?}
    """
    data = request.get_json(silent=True) or {}
    if not data.get("trigger_type"):
        return jsonify({"error": True, "message": "trigger_type requis"}), 400

    session = _get_session()
    try:
        inv = Investigation(
            trigger_type=data["trigger_type"],
            trigger_id=data.get("trigger_id"),
            hypothesis=data.get("hypothesis"),
            data_plan=data.get("data_plan"),
            data_collected=data.get("data_collected"),
            conclusion=data.get("conclusion"),
            decision=data.get("decision"),
            ecr_id=data.get("ecr_id"),
            mca_id=data.get("mca_id"),
            completed_at=datetime.now(timezone.utc) if data.get("decision") else None,
        )
        session.add(inv)
        session.commit()
        return jsonify({"success": True, "investigation": _investigation_to_dict(inv)}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


# ── Seed ─────────────────────────────────────────────────────────────────────

@aftersales_bp.route("/aftersales/seed", methods=["POST"])
def seed():
    """Initialise les ECR/MCA depuis l'analyse Aftersales Mai 2026. Idempotent."""
    session = _get_session()
    try:
        created = seed_aftersales_data(session)
        return jsonify({"success": True, "created": created})
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc)}), 500
    finally:
        session.close()


# ── Vue admin (dev) ───────────────────────────────────────────────────────────

@aftersales_bp.route("/dev/aftersales", methods=["GET"])
def dev_aftersales():
    """Vue d'ensemble admin : ECRs ouverts, MCAs à appliquer, dernières investigations."""
    session = _get_session()
    try:
        open_ecrs = session.query(ECR).filter(
            ECR.status.in_(["a_transmettre", "en_cours"])
        ).order_by(ECR.ecr_number).all()

        pending_mcas = session.query(MCA).filter(
            MCA.status.in_(["a_appliquer", "en_attente"])
        ).order_by(MCA.mca_number).all()

        recent_investigations = (
            session.query(Investigation)
            .order_by(Investigation.created_at.desc())
            .limit(10)
            .all()
        )

        return jsonify({
            "open_ecr": [_ecr_to_dict(e) for e in open_ecrs],
            "pending_mca": [_mca_to_dict(m) for m in pending_mcas],
            "recent_investigations": [_investigation_to_dict(i) for i in recent_investigations],
            "counts": {
                "open_ecr": len(open_ecrs),
                "pending_mca": len(pending_mcas),
            },
        })
    finally:
        session.close()
