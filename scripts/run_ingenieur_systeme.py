#!/usr/bin/env python3
"""Pipeline d'ingénierie — Ingénieurs Système.

Usage :
  python scripts/run_ingenieur_systeme.py --ecr ECR-017
      Lance tous les IS assignés dans le Product Brief (auto-détection)
      Si multi-domaines : Round 1 (SFD+ICD) → Arbitrage → Round 2 (REQ+DVP)

  python scripts/run_ingenieur_systeme.py --ecr ECR-017 --domain IS-6
      Lance uniquement l'IS du domaine spécifié

  python scripts/run_ingenieur_systeme.py --show ECR-017
      Affiche tous les documents d'ingénierie pour un ECR

  python scripts/run_ingenieur_systeme.py --approve SFD-ECR017-IS6
      Marque un document comme approuvé

  python scripts/run_ingenieur_systeme.py --return SFD-ECR017-IS6 "Commentaire"
      Retourne un document en révision avec commentaire

Domaines disponibles : IS-1 IS-2 IS-3 IS-4 IS-5 IS-6
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DOC_TYPE_LABELS = {
    "package":       "Package",
    "product_brief": "Product Brief",
    "sfd":           "SFD — System Functional Description",
    "icd":           "ICD — Interface Control Document",
    "arbitrage":     "Arbitrage",
    "req":           "REQ — Requis Système",
    "dvp":           "DVP — Design Validation Plan",
    "design_review": "Design Review",
}


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


def _get_pb_domains(session, ecr_number: str) -> list[str]:
    """Récupère la liste des IS assignés depuis le Product Brief."""
    from core.models import ECR, EngineeringDocument

    ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
    if not ecr:
        return []

    pb = (
        session.query(EngineeringDocument)
        .filter_by(ecr_id=ecr.id, doc_type="product_brief")
        .order_by(EngineeringDocument.id.desc())
        .first()
    )
    if not pb:
        return []

    content = json.loads(pb.content)
    return [a["domain"] for a in content.get("is_assignments", [])]


def _print_doc_summary(doc) -> None:
    """Affiche un résumé lisible d'un document d'ingénierie."""
    content = json.loads(doc.content) if doc.content else {}
    label = DOC_TYPE_LABELS.get(doc.doc_type, doc.doc_type.upper())
    domain_label = f" [{doc.is_domain}]" if doc.is_domain else " [AP]"
    status_icon = {"approuve": "✅", "soumis": "📄", "rejete": "❌", "en_revision": "🔄"}.get(doc.status, "·")

    print(f"\n{status_icon} {doc.doc_number}{domain_label} — {label}")
    print(f"   Titre : {doc.title}")
    print(f"   Statut : {doc.status}  |  Créé : {doc.created_at.strftime('%Y-%m-%d %H:%M')}")

    if doc.doc_type == "sfd":
        print(f"   Description : {str(content.get('functional_description', ''))[:200]}")
        behaviors = content.get("behaviors", [])
        if behaviors:
            print(f"   Comportements : {len(behaviors)} définis")

    elif doc.doc_type == "icd":
        interfaces = content.get("interfaces", [])
        print(f"   Interfaces : {len(interfaces)} définies")
        for ifc in interfaces[:3]:
            print(f"     · {ifc.get('interface_id','')} : {ifc.get('description','')[:80]}")

    elif doc.doc_type == "arbitrage":
        conflicts = content.get("conflicts", [])
        contracts = content.get("interface_contracts", [])
        print(f"   Conflits résolus : {len(conflicts)}  |  Contrats : {len(contracts)}")
        print(f"   Synthèse : {content.get('assessment','')[:200]}")

    elif doc.doc_type == "req":
        reqs = content.get("requirements", [])
        print(f"   REQs : {len(reqs)}")
        for r in reqs[:3]:
            print(f"     · {r.get('req_id','')} : {r.get('title','')[:70]}")

    elif doc.doc_type == "dvp":
        cases = content.get("test_cases", [])
        types = {}
        for tc in cases:
            t = tc.get("type", "?")
            types[t] = types.get(t, 0) + 1
        print(f"   Cas de test : {len(cases)}  ({', '.join(f'{v} {k}' for k,v in types.items())})")
        print(f"   Succès : {content.get('success_criteria','')[:120]}")

    if doc.review_notes:
        print(f"   ↳ Note revue : {doc.review_notes[:120]}")


def cmd_run(session, config, ecr_number: str, domain_filter: str | None) -> int:
    from agents.ingenieur_systeme_agent import IngenieurSystemeAgent
    from agents.architecte_produit_agent import ArchitecteProduitAgent

    # Déterminer les domaines IS à lancer
    if domain_filter:
        domains = [domain_filter]
    else:
        domains = _get_pb_domains(session, ecr_number)
        if not domains:
            print(f"[ERREUR] Aucun Product Brief trouvé pour {ecr_number}.")
            print(f"         Lancez d'abord : python scripts/run_architecte_produit.py --brief {ecr_number}")
            return 1

    is_agent = IngenieurSystemeAgent(config)
    ap_agent = ArchitecteProduitAgent(config)
    is_multi = len(domains) > 1

    print(f"[IS] ECR : {ecr_number} — Domaines : {', '.join(domains)}")
    if is_multi:
        print(f"[IS] Multi-domaines → Round 1 (SFD+ICD) puis Arbitrage puis Round 2 (REQ+DVP)")
    else:
        print(f"[IS] Mono-domaine → SFD + ICD + REQ + DVP en un seul passage")

    # ---- Round 1 : SFD + ICD ----
    print("\n[IS] Round 1 — SFD + ICD...")
    for domain in domains:
        print(f"  → {domain} : génération SFD + ICD...")
        docs = is_agent.run_draft(session, ecr_number, domain)
        if not docs:
            print(f"  [ERREUR] {domain} : échec de génération")
            session.rollback()
            return 1
        for dtype, doc in docs.items():
            print(f"     ✓ {doc.doc_number}")
    session.commit()

    # ---- Arbitrage (si multi-domaines) ----
    if is_multi:
        print("\n[AP] Arbitrage cross-domaines...")
        arb_doc = ap_agent.arbitrate(session, ecr_number)
        if not arb_doc:
            print("[ERREUR] Arbitrage échoué")
            session.rollback()
            return 1
        session.commit()
        print(f"     ✓ {arb_doc.doc_number}")

        # Afficher le résumé de l'arbitrage
        arb_content = json.loads(arb_doc.content)
        print(f"\n  Synthèse : {arb_content.get('assessment','')[:200]}")
        conflicts = arb_content.get("conflicts", [])
        if conflicts:
            print(f"  Conflits résolus : {len(conflicts)}")
            for c in conflicts:
                print(f"    · {c.get('description','')[:80]}")
                print(f"      → {c.get('decision','')[:80]}")
        contracts = arb_content.get("interface_contracts", [])
        if contracts:
            print(f"  Contrats d'interface : {len(contracts)}")
            for ifc in contracts:
                print(f"    · {ifc.get('interface_id','')} : {ifc.get('producer','')} → {ifc.get('consumer','')}")

    # ---- Round 2 : REQ + DVP ----
    print("\n[IS] Round 2 — REQ + DVP...")
    for domain in domains:
        print(f"  → {domain} : génération REQ + DVP...")
        docs = is_agent.run_completion(session, ecr_number, domain)
        if not docs:
            print(f"  [ERREUR] {domain} : échec de génération")
            session.rollback()
            return 1
        for dtype, doc in docs.items():
            print(f"     ✓ {doc.doc_number}")
    session.commit()

    print(f"\n[OK] Ingénierie complète pour {ecr_number}")
    print(f"     Consulter : python scripts/run_ingenieur_systeme.py --show {ecr_number}")
    print(f"     Design Review : python scripts/run_architecte_produit.py --design-review {ecr_number}")
    return 0


def cmd_show(session, ecr_number: str) -> int:
    from core.models import ECR, EngineeringDocument

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

    print(f"\n{'='*65}")
    print(f"  {ecr_number} [{ecr.status}]")
    print(f"  {ecr.title}")
    print(f"{'='*65}")

    if not docs:
        print("\n  Aucun document — lancez le pipeline d'abord.\n")
        return 0

    for doc in docs:
        _print_doc_summary(doc)

    print()
    return 0


def cmd_approve(session, doc_number: str) -> int:
    from core.models import EngineeringDocument
    from datetime import datetime, timezone

    doc = session.query(EngineeringDocument).filter_by(doc_number=doc_number).first()
    if not doc:
        print(f"[ERREUR] Document {doc_number} introuvable")
        return 1

    doc.status = "approuve"
    doc.updated_at = datetime.now(timezone.utc)
    session.commit()
    print(f"[OK] {doc_number} → approuvé")
    return 0


def cmd_return(session, doc_number: str, comment: str) -> int:
    from core.models import EngineeringDocument
    from datetime import datetime, timezone

    doc = session.query(EngineeringDocument).filter_by(doc_number=doc_number).first()
    if not doc:
        print(f"[ERREUR] Document {doc_number} introuvable")
        return 1

    doc.status = "en_revision"
    doc.review_notes = comment
    doc.updated_at = datetime.now(timezone.utc)
    session.commit()
    print(f"[OK] {doc_number} → en_revision")
    print(f"     Note : {comment}")
    return 0


def main() -> int:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    session, config = _get_session()

    try:
        if "--ecr" in args:
            idx = args.index("--ecr")
            if idx + 1 >= len(args):
                print("[ERREUR] --ecr requiert un numéro d'ECR (ex: ECR-017)")
                return 1
            ecr_number = args[idx + 1]
            domain = None
            if "--domain" in args:
                d_idx = args.index("--domain")
                if d_idx + 1 < len(args):
                    domain = args[d_idx + 1]
            return cmd_run(session, config, ecr_number, domain)

        elif "--show" in args:
            idx = args.index("--show")
            if idx + 1 >= len(args):
                print("[ERREUR] --show requiert un numéro d'ECR")
                return 1
            return cmd_show(session, args[idx + 1])

        elif "--approve" in args:
            idx = args.index("--approve")
            if idx + 1 >= len(args):
                print("[ERREUR] --approve requiert un numéro de document")
                return 1
            return cmd_approve(session, args[idx + 1])

        elif "--return" in args:
            idx = args.index("--return")
            if idx + 2 >= len(args):
                print("[ERREUR] --return requiert un numéro de document et un commentaire")
                return 1
            return cmd_return(session, args[idx + 1], args[idx + 2])

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
