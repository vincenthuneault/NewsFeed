#!/usr/bin/env python3
"""Pipeline d'ingénierie — Architecte Produit.

Usage :
  python scripts/run_architecte_produit.py --package
      Propose un package d'ingénierie (analyse les ECRs a_transmettre)

  python scripts/run_architecte_produit.py --approve PKG-001
      Approuve le package : ECRs inclus → en_cours

  python scripts/run_architecte_produit.py --approve PKG-001 --reject ECR-004 "doublon ECR-001"
      Approuve avec rejet explicite d'un ECR

  python scripts/run_architecte_produit.py --brief ECR-017
      Génère le Product Brief pour un ECR en_cours

  python scripts/run_architecte_produit.py --design-review ECR-017
      Lance la Design Review de l'ensemble des docs IS

  python scripts/run_architecte_produit.py --show
      Affiche l'état global du pipeline d'ingénierie

  python scripts/run_architecte_produit.py --show ECR-017
      Affiche tous les docs pour un ECR spécifique
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _get_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.config import load_config
    from core.models import Base

    config = load_config()
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), config


def _print_pkg(content: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  ANALYSE DU BACKLOG")
    print(f"{'='*60}")
    print(f"\n{content.get('analysis', '')}\n")

    included, deferred, cancelled = [], [], []
    for d in content.get("ecr_decisions", []):
        if d["action"] == "inclure":
            included.append(d)
        elif d["action"] == "annuler":
            cancelled.append(d)
        else:
            deferred.append(d)

    if included:
        print("PACKAGE RECOMMANDÉ (max 3) :")
        for d in sorted(included, key=lambda x: x.get("priority_order", 99)):
            domains = ", ".join(a["domain"] for a in d.get("is_assignments", []))
            print(f"  #{d.get('priority_order','?')} {d['ecr_number']} [{domains}]")
            print(f"     {d['justification']}")
            for a in d.get("is_assignments", []):
                print(f"     → {a['domain']} : {a['responsibility']}")
        print()

    if cancelled:
        print("À ANNULER :")
        for d in cancelled:
            print(f"  ✗ {d['ecr_number']} — {d['justification']}")
        print()

    if deferred:
        print("DIFFÉRÉS :")
        for d in deferred:
            print(f"  ⏸ {d['ecr_number']} — {d['justification']}")
        print()


def _print_pb(doc) -> None:
    content = json.loads(doc.content)
    print(f"\n{'='*60}")
    print(f"  {doc.doc_number} — {doc.title}")
    print(f"{'='*60}")
    print(f"\nINTENT : {content.get('intent', '')}")
    print(f"IMPACT : {content.get('user_impact', '')}\n")

    print("INGÉNIEURS ASSIGNÉS :")
    for a in content.get("is_assignments", []):
        print(f"  {a['domain']} : {a['responsibility']}")

    print("\nCRITÈRES DE SUCCÈS :")
    for c in content.get("success_criteria", []):
        print(f"  ✓ {c}")

    print("\nCONTRAINTES :")
    for c in content.get("constraints", []):
        print(f"  ! {c}")

    if content.get("out_of_scope"):
        print("\nHORS SCOPE :")
        for s in content.get("out_of_scope", []):
            print(f"  ✗ {s}")

    if content.get("notes_for_is"):
        print(f"\nNOTES IS : {content['notes_for_is']}")
    print()


def _print_review(doc) -> None:
    content = json.loads(doc.content)
    decision = content.get("overall_decision", "?")
    icon = "✅" if decision == "approuve" else "🔄"
    print(f"\n{'='*60}")
    print(f"  {doc.doc_number} — Design Review {icon} {decision.upper()}")
    print(f"{'='*60}")
    print(f"\n{content.get('summary', '')}\n")

    for d in content.get("per_domain", []):
        dom_icon = "✅" if d.get("domain_decision") == "approuve" else "🔄"
        print(f"  {dom_icon} {d['domain']} : SFD={'✓' if d.get('sfd_ok') else '✗'} "
              f"ICD={'✓' if d.get('icd_ok') else '✗'} "
              f"REQ={'✓' if d.get('req_ok') else '✗'} "
              f"DVP={'✓' if d.get('dvp_ok') else '✗'}")
        for issue in d.get("issues", []):
            print(f"     ↳ {issue}")

    if content.get("blocking_issues"):
        print("\nBLOQUANTS :")
        for b in content["blocking_issues"]:
            print(f"  ✗ {b}")
    print()


def _print_engineering_status(session) -> None:
    from core.models import ECR, EngineeringDocument

    print(f"\n{'='*60}")
    print("  ÉTAT DU PIPELINE D'INGÉNIERIE")
    print(f"{'='*60}\n")

    # ECRs en_cours
    en_cours = session.query(ECR).filter(ECR.status == "en_cours").all()
    if en_cours:
        print("ECRs EN COURS :")
        for e in en_cours:
            docs = session.query(EngineeringDocument).filter_by(ecr_id=e.id).all()
            doc_types = {d.doc_type for d in docs}
            pb = "✓" if "product_brief" in doc_types else "·"
            sfd = "✓" if "sfd" in doc_types else "·"
            icd = "✓" if "icd" in doc_types else "·"
            arb = "✓" if "arbitrage" in doc_types else "·"
            req = "✓" if "req" in doc_types else "·"
            dvp = "✓" if "dvp" in doc_types else "·"
            dr = "✓" if "design_review" in doc_types else "·"
            print(f"  {e.ecr_number} — {e.title[:50]}")
            print(f"     PB:{pb} SFD:{sfd} ICD:{icd} ARB:{arb} REQ:{req} DVP:{dvp} DR:{dr}")
        print()

    # Packages
    pkgs = (
        session.query(EngineeringDocument)
        .filter_by(doc_type="package")
        .order_by(EngineeringDocument.id.desc())
        .limit(3)
        .all()
    )
    if pkgs:
        print("DERNIERS PACKAGES :")
        for p in pkgs:
            print(f"  {p.doc_number} [{p.status}] — {p.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()

    # ECRs a_transmettre
    waiting = session.query(ECR).filter(ECR.status == "a_transmettre").count()
    print(f"ECRs en attente de package : {waiting}")
    print()


def cmd_package(session, config) -> int:
    from agents.architecte_produit_agent import ArchitecteProduitAgent

    print("[AP] Analyse du backlog en cours...")
    agent = ArchitecteProduitAgent(config)
    doc = agent.propose_package(session)
    if not doc:
        print("[OK] Aucun ECR à traiter.")
        return 0

    session.commit()
    content = json.loads(doc.content)
    _print_pkg(content)
    print(f"[OK] Package {doc.doc_number} proposé — pour approuver :")
    print(f"     python scripts/run_architecte_produit.py --approve {doc.doc_number}")
    return 0


def cmd_approve(session, config, pkg_number: str, rejections: dict) -> int:
    from agents.architecte_produit_agent import ArchitecteProduitAgent

    agent = ArchitecteProduitAgent(config)
    try:
        summary = agent.approve_package(session, pkg_number, rejections)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1

    print(f"[OK] {pkg_number} approuvé")
    if summary["en_cours"]:
        print(f"  → en_cours : {summary['en_cours']}")
        print(f"     Prochaine étape : générer les Product Briefs")
        for ecr in summary["en_cours"]:
            print(f"     python scripts/run_architecte_produit.py --brief {ecr}")
    if summary["annule"]:
        print(f"  → annulés  : {summary['annule']}")
    if summary["differe"]:
        print(f"  → différés : {summary['differe']}")
    return 0


def cmd_brief(session, config, ecr_number: str) -> int:
    from agents.architecte_produit_agent import ArchitecteProduitAgent

    print(f"[AP] Génération du Product Brief pour {ecr_number}...")
    agent = ArchitecteProduitAgent(config)
    try:
        doc = agent.create_product_brief(session, ecr_number)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1

    if not doc:
        return 1

    session.commit()
    _print_pb(doc)
    content = json.loads(doc.content)
    domains = [a["domain"] for a in content.get("is_assignments", [])]
    print(f"[OK] {doc.doc_number} créé — prochaine étape :")
    print(f"     python scripts/run_ingenieur_systeme.py --ecr {ecr_number}")
    if len(domains) > 1:
        print(f"     (Multi-domaines : {', '.join(domains)} — arbitrage automatique)")
    return 0


def cmd_design_review(session, config, ecr_number: str) -> int:
    from agents.architecte_produit_agent import ArchitecteProduitAgent

    print(f"[AP] Design Review pour {ecr_number}...")
    agent = ArchitecteProduitAgent(config)
    try:
        doc = agent.design_review(session, ecr_number)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1

    if not doc:
        return 1

    session.commit()
    _print_review(doc)
    content = json.loads(doc.content)
    if content.get("overall_decision") == "approuve":
        print("[OK] Design Review approuvée — le développement peut commencer.")
    else:
        print("[!] Design Review retournée — corriger les issues puis relancer.")
        print(f"    python scripts/run_ingenieur_systeme.py --ecr {ecr_number}")
    return 0


def cmd_show(session, ecr_number: str | None) -> int:
    from core.models import ECR, EngineeringDocument

    if not ecr_number:
        _print_engineering_status(session)
        return 0

    ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
    if not ecr:
        print(f"[ERREUR] ECR {ecr_number} introuvable")
        return 1

    docs = (
        session.query(EngineeringDocument)
        .filter_by(ecr_id=ecr.id)
        .order_by(EngineeringDocument.id)
        .all()
    )

    print(f"\n{'='*60}")
    print(f"  {ecr_number} [{ecr.status}] — {ecr.title}")
    print(f"{'='*60}\n")

    if not docs:
        print("  Aucun document d'ingénierie.\n")
        return 0

    for doc in docs:
        domain_label = f" [{doc.is_domain}]" if doc.is_domain else " [AP]"
        status_icon = {"approuve": "✅", "soumis": "📄", "rejete": "❌", "en_revision": "🔄"}.get(doc.status, "·")
        print(f"  {status_icon} {doc.doc_number}{domain_label} — {doc.title[:55]}")
        if doc.review_notes:
            print(f"     Note : {doc.review_notes[:100]}")

    print()

    # Afficher le détail du dernier document de chaque type
    shown_types = set()
    for doc in reversed(docs):
        if doc.doc_type not in shown_types and doc.content:
            shown_types.add(doc.doc_type)
            content = json.loads(doc.content)
            print(f"\n--- {doc.doc_number} ---")
            print(json.dumps(content, ensure_ascii=False, indent=2)[:2000])

    return 0


def main() -> int:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    session, config = _get_session()

    try:
        if "--package" in args:
            return cmd_package(session, config)

        elif "--approve" in args:
            idx = args.index("--approve")
            if idx + 1 >= len(args):
                print("[ERREUR] --approve requiert un numéro de package (ex: PKG-001)")
                return 1
            pkg_number = args[idx + 1]
            rejections = {}
            if "--reject" in args:
                r_idx = args.index("--reject")
                if r_idx + 2 < len(args):
                    rejections[args[r_idx + 1]] = args[r_idx + 2]
            return cmd_approve(session, config, pkg_number, rejections)

        elif "--brief" in args:
            idx = args.index("--brief")
            if idx + 1 >= len(args):
                print("[ERREUR] --brief requiert un numéro d'ECR (ex: ECR-017)")
                return 1
            return cmd_brief(session, config, args[idx + 1])

        elif "--design-review" in args:
            idx = args.index("--design-review")
            if idx + 1 >= len(args):
                print("[ERREUR] --design-review requiert un numéro d'ECR")
                return 1
            return cmd_design_review(session, config, args[idx + 1])

        elif "--show" in args:
            idx = args.index("--show")
            ecr = args[idx + 1] if idx + 1 < len(args) and not args[idx + 1].startswith("--") else None
            return cmd_show(session, ecr)

        else:
            print(f"[ERREUR] Argument inconnu : {args}")
            print("Utilisez --help pour la liste des commandes.")
            return 1

    except Exception as exc:
        import traceback
        print(f"[ERREUR] {exc}")
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
