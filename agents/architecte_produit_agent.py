"""Agent Architecte Produit — pilote le pipeline d'ingénierie.

Quatre opérations :
  propose_package()       — analyse les ECRs, propose un package
  create_product_brief()  — produit le PB par ECR approuvé
  arbitrate()             — arbitre les drafts IS multi-domaines
  design_review()         — valide SFD+ICD+REQ+DVP vs PB
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from sqlalchemy.orm import Session

from core.logger import get_logger
from core.models import ECR, ECRStatusHistory, EngineeringDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_AP_BASE = """\
Tu es l'agent Architecte Produit d'un fil d'information personnalisé.
Tu pilotes le pipeline d'ingénierie : tu prépares, analyses et recommandes.
L'utilisateur valide toutes les décisions finales.

## Vue produit

Système : fil de nouvelles personnalisé généré quotidiennement par des agents IA.
Stack : Python · Flask · SQLite · Claude Sonnet · Google TTS fr-CA · YouTube API · RSS.

Architecture en 4 couches :
  [Journalistes] → collectent les articles bruts par sujet (max 5/jour)
  [Pipeline]     → déduplique · résume (Claude) · image · audio (TTS)
  [API REST]     → Flask + Gunicorn · sert JSON + fichiers statiques
  [Frontend]     → Vanilla JS · CSS scroll-snap · PWA mobile

Profil utilisateur : homme francophone ~35 ans, Contrecoeur/Sorel-Tracy/Grand Montréal.
Intérêts : politique US/CA/QC, tech/IA, espace, véhicules EV, EDM.
Exclusions : sport, jeux vidéo, contenu jeunesse, Bollywood, K-pop.

## Domaines IS

IS-1 Agents & Collecte     → agents/*, core/orchestrator.py
IS-2 Pipeline & Traitement → core/pipeline.py, processors/*
IS-3 IA & Contenu          → processors/summarizer.py, tts_generator.py, image_extractor.py
IS-4 Backend & Données     → core/models.py, backend/app.py, backend/api/*
IS-5 Frontend Mobile       → frontend/js/*, frontend/css/*, frontend/sw.js
IS-6 Infrastructure        → config/config.yaml, deploy/*, core/logger.py

## Règles de priorisation ECR

- ECR bloquant (feed cassé, données perdues) → toujours en tête
- ECR haute priorité + haute sévérité → inclure sauf raison technique majeure
- ECR dépendant d'un ECR non résolu → différer
- Maximum 3 ECRs par package
- Un ECR doublon d'un autre → annuler le doublon
"""

_PKG_SYSTEM = _AP_BASE + """
## Opération : Proposition de package

Analyse les ECRs fournis et propose un package d'ingénierie de max 3 ECRs.
Pour chaque ECR : action inclure | annuler | differer + justification + domaines IS impliqués.

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "analysis": "Analyse globale du backlog en 2-3 phrases",
  "ecr_decisions": [
    {
      "ecr_number": "ECR-017",
      "action": "inclure",
      "justification": "Raison en une phrase",
      "is_assignments": [
        {"domain": "IS-6", "responsibility": "Ce que ce domaine doit traiter"}
      ],
      "priority_order": 1
    }
  ]
}
"""

_PB_SYSTEM = _AP_BASE + """
## Opération : Product Brief

Produis un Product Brief complet pour l'ECR fourni.
Le PB est le document de référence que les Ingénieurs Système liront en premier.
Il doit être précis, actionnable et définir clairement les boundaries de chaque IS.

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "ecr_number": "ECR-017",
  "intent": "Ce qu'on veut obtenir du point de vue utilisateur",
  "user_impact": "Impact concret sur l'expérience utilisateur",
  "is_assignments": [
    {
      "domain": "IS-6",
      "responsibility": "Ce que ce domaine doit produire, en une phrase précise"
    }
  ],
  "constraints": [
    "Contrainte non-négociable 1",
    "Contrainte non-négociable 2"
  ],
  "success_criteria": [
    "Comment on sait que c'est réglé — observable et mesurable"
  ],
  "out_of_scope": [
    "Ce qui NE fait PAS partie de ce fix"
  ],
  "notes_for_is": "Instructions ou mises en garde spécifiques pour les IS"
}
"""

_ARB_SYSTEM = """\
Tu es l'Arbitre technique du pipeline d'ingénierie d'un fil d'information personnalisé.

Ton rôle : lire les drafts SFD + ICD de deux Ingénieurs Système sur le même ECR,
identifier les conflits d'interface ou de conception, et rendre une décision contraignante.

Les IS compléteront leur REQ + DVP en respectant tes arbitrages. Ta décision est finale.

Principes d'arbitrage :
- Privilégier la solution la plus simple qui satisfait le Product Brief
- Les contrats d'interface doivent être sans ambiguïté (format, déclencheur, producteur, consommateur)
- Si les deux positions sont compatibles, formalise l'interface et valide les deux
- Si contradiction : choisis en justifiant selon l'impact utilisateur et la maintenabilité

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "ecr_number": "ECR-017",
  "assessment": "Résumé de la situation en 2-3 phrases",
  "conflicts": [
    {
      "description": "Nature du conflit",
      "domain1_position": "Position IS-X",
      "domain2_position": "Position IS-Y",
      "decision": "Décision contraignante",
      "rationale": "Justification"
    }
  ],
  "interface_contracts": [
    {
      "interface_id": "IFC-ECR017-001",
      "producer": "IS-2",
      "consumer": "IS-6",
      "description": "Ce qui est transmis",
      "data_format": "Type et structure exacte",
      "trigger": "Quand l'interface est invoquée",
      "error_handling": "Comportement en cas d'échec"
    }
  ],
  "constraints_per_domain": {
    "IS-6": ["Contrainte imposée à IS-6"],
    "IS-2": ["Contrainte imposée à IS-2"]
  }
}
"""

_REVIEW_SYSTEM = _AP_BASE + """
## Opération : Design Review

Valide que l'ensemble SFD + ICD + REQ + DVP produits par les IS répond au Product Brief.

Évalue pour chaque IS :
1. SFD cohérent avec l'intent du PB ?
2. ICD ferme toutes les interfaces (pas de gap entre domaines) ?
3. REQs complets, testables et tracés au PB ?
4. DVP couvre cas normaux + cas limites + régressions ?

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "ecr_number": "ECR-017",
  "overall_decision": "approuve | retourne",
  "summary": "Synthèse en 2-3 phrases",
  "per_domain": [
    {
      "domain": "IS-6",
      "sfd_ok": true,
      "icd_ok": true,
      "req_ok": true,
      "dvp_ok": false,
      "issues": ["Ce qui manque ou est incohérent"],
      "domain_decision": "approuve | retourne"
    }
  ],
  "blocking_issues": ["Problèmes bloquant l'approbation globale"],
  "recommendations": ["Suggestions non-bloquantes"]
}
"""

_MAX_TOKENS = 2500
_TEMPERATURE = 0.2


class ArchitecteProduitAgent:
    """Pilote le pipeline d'ingénierie — package, briefs, arbitrage, design review."""

    def __init__(self, config: dict) -> None:
        self._log = get_logger("agents.architecte_produit", config.get("logging"))
        model = config.get("claude", {}).get("model", "claude-sonnet-4-6")
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    # ------------------------------------------------------------------ #
    # Opération 1 — Package                                               #
    # ------------------------------------------------------------------ #

    def propose_package(self, session: Session) -> EngineeringDocument | None:
        """Analyse les ECRs a_transmettre et propose un package de max 3 ECRs."""
        ecrs = (
            session.query(ECR)
            .filter(ECR.status == "a_transmettre")
            .order_by(ECR.id)
            .all()
        )
        if not ecrs:
            self._log.info("AP — aucun ECR a_transmettre")
            return None

        ecrs_json = json.dumps([{
            "ecr_number": e.ecr_number,
            "title": e.title,
            "priority": e.priority,
            "severity": e.severity,
            "symptom": e.symptom,
            "root_cause": e.root_cause,
            "proposed_fix": e.proposed_fix,
        } for e in ecrs], ensure_ascii=False, indent=2)

        # Récupérer les ECRs déjà en cours pour contexte
        en_cours = session.query(ECR).filter(ECR.status == "en_cours").all()
        context = ""
        if en_cours:
            context = f"\nECRs déjà en cours (ne pas redoubler) : {[e.ecr_number for e in en_cours]}\n"

        result = self._call_claude(
            system=_PKG_SYSTEM,
            user_prompt=f"ECRs en attente :{context}\n{ecrs_json}",
        )
        if not result:
            return None

        doc_number = self._next_doc_number(session, "PKG")
        doc = self._save_doc(
            session,
            doc_number=doc_number,
            doc_type="package",
            ecr_id=None,
            is_domain=None,
            title=f"Package d'ingénierie {doc_number}",
            content=json.dumps(result, ensure_ascii=False),
        )
        self._log.info("AP — package proposé", extra={"doc": doc_number})
        return doc

    def approve_package(
        self,
        session: Session,
        pkg_number: str,
        extra_rejections: dict[str, str] | None = None,
    ) -> dict:
        """Approuve un package : passe les ECRs inclus en_cours, annule les rejetés."""
        doc = session.query(EngineeringDocument).filter_by(doc_number=pkg_number).first()
        if not doc:
            raise ValueError(f"Package {pkg_number} introuvable")

        content = json.loads(doc.content)
        extra_rejections = extra_rejections or {}
        summary = {"en_cours": [], "annule": [], "differe": []}
        now = datetime.now(timezone.utc)

        for decision in content.get("ecr_decisions", []):
            ecr_number = decision["ecr_number"]
            action = decision["action"]

            if ecr_number in extra_rejections:
                action = "annuler"
                decision["justification"] = extra_rejections[ecr_number]

            ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
            if not ecr:
                continue

            if action == "inclure":
                old = ecr.status
                ecr.status = "en_cours"
                ecr.updated_at = now
                session.add(ECRStatusHistory(
                    ecr_id=ecr.id,
                    old_status=old,
                    new_status="en_cours",
                    note=f"Approuvé dans {pkg_number} — {decision.get('justification', '')}",
                    changed_at=now,
                ))
                summary["en_cours"].append(ecr_number)

            elif action == "annuler":
                old = ecr.status
                ecr.status = "annule"
                ecr.updated_at = now
                ecr.closed_at = now
                session.add(ECRStatusHistory(
                    ecr_id=ecr.id,
                    old_status=old,
                    new_status="annule",
                    note=f"Annulé lors de {pkg_number} — {decision.get('justification', '')}",
                    changed_at=now,
                ))
                summary["annule"].append(ecr_number)

            else:
                summary["differe"].append(ecr_number)

        doc.status = "approuve"
        doc.updated_at = now
        session.commit()
        self._log.info("AP — package approuvé", extra={"pkg": pkg_number, **summary})
        return summary

    # ------------------------------------------------------------------ #
    # Opération 2 — Product Brief                                         #
    # ------------------------------------------------------------------ #

    def create_product_brief(self, session: Session, ecr_number: str) -> EngineeringDocument | None:
        """Produit le Product Brief pour un ECR en_cours."""
        ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
        if not ecr:
            raise ValueError(f"ECR {ecr_number} introuvable")

        # Récupérer le package associé pour contexte
        pkg_context = ""
        all_pkgs = (
            session.query(EngineeringDocument)
            .filter_by(doc_type="package", status="approuve")
            .order_by(EngineeringDocument.id.desc())
            .first()
        )
        if all_pkgs:
            pkg_data = json.loads(all_pkgs.content)
            for d in pkg_data.get("ecr_decisions", []):
                if d["ecr_number"] == ecr_number:
                    pkg_context = f"\nContexte package :\n{json.dumps(d, ensure_ascii=False)}\n"
                    break

        ecr_json = json.dumps({
            "ecr_number": ecr.ecr_number,
            "title": ecr.title,
            "symptom": ecr.symptom,
            "root_cause": ecr.root_cause,
            "proposed_fix": ecr.proposed_fix,
            "priority": ecr.priority,
            "severity": ecr.severity,
        }, ensure_ascii=False, indent=2)

        result = self._call_claude(
            system=_PB_SYSTEM,
            user_prompt=f"ECR à briefer :{pkg_context}\n{ecr_json}",
        )
        if not result:
            return None

        doc_number = f"PB-{ecr_number}"
        existing = session.query(EngineeringDocument).filter_by(doc_number=doc_number).first()
        if existing:
            # Nouvelle version
            doc_number = f"PB-{ecr_number}-v{existing.version + 1}"

        doc = self._save_doc(
            session,
            doc_number=doc_number,
            doc_type="product_brief",
            ecr_id=ecr.id,
            is_domain=None,
            title=f"Product Brief — {ecr.title[:60]}",
            content=json.dumps(result, ensure_ascii=False),
        )
        self._log.info("AP — Product Brief créé", extra={"doc": doc_number, "ecr": ecr_number})
        return doc

    # ------------------------------------------------------------------ #
    # Opération 3 — Arbitrage                                             #
    # ------------------------------------------------------------------ #

    def arbitrate(self, session: Session, ecr_number: str) -> EngineeringDocument | None:
        """Arbitre les drafts SFD+ICD de plusieurs IS sur le même ECR."""
        ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
        if not ecr:
            raise ValueError(f"ECR {ecr_number} introuvable")

        # Récupérer le PB
        pb_doc = (
            session.query(EngineeringDocument)
            .filter_by(ecr_id=ecr.id, doc_type="product_brief")
            .order_by(EngineeringDocument.id.desc())
            .first()
        )
        if not pb_doc:
            raise ValueError(f"Aucun Product Brief trouvé pour {ecr_number} — lancez --brief d'abord")

        # Récupérer tous les drafts SFD + ICD
        drafts = (
            session.query(EngineeringDocument)
            .filter(
                EngineeringDocument.ecr_id == ecr.id,
                EngineeringDocument.doc_type.in_(["sfd", "icd"]),
                EngineeringDocument.status == "soumis",
            )
            .all()
        )

        domains = list({d.is_domain for d in drafts if d.is_domain})
        if len(domains) < 2:
            self._log.info("AP — mono-domaine, pas d'arbitrage nécessaire")
            return None

        # Construire le prompt d'arbitrage
        drafts_by_domain: dict[str, dict] = {}
        for d in drafts:
            if d.is_domain not in drafts_by_domain:
                drafts_by_domain[d.is_domain] = {}
            drafts_by_domain[d.is_domain][d.doc_type] = json.loads(d.content)

        user_prompt = (
            f"Product Brief :\n{pb_doc.content}\n\n"
            + "\n\n".join(
                f"--- Drafts {domain} ---\n{json.dumps(docs, ensure_ascii=False, indent=2)}"
                for domain, docs in drafts_by_domain.items()
            )
        )

        result = self._call_claude(system=_ARB_SYSTEM, user_prompt=user_prompt, max_tokens=3000)
        if not result:
            return None

        doc_number = f"ARB-{ecr_number}"
        doc = self._save_doc(
            session,
            doc_number=doc_number,
            doc_type="arbitrage",
            ecr_id=ecr.id,
            is_domain=None,
            title=f"Arbitrage — {ecr_number} ({' / '.join(domains)})",
            content=json.dumps(result, ensure_ascii=False),
        )
        self._log.info("AP — arbitrage produit", extra={"doc": doc_number, "domaines": domains})
        return doc

    # ------------------------------------------------------------------ #
    # Opération 4 — Design Review                                         #
    # ------------------------------------------------------------------ #

    def design_review(self, session: Session, ecr_number: str) -> EngineeringDocument | None:
        """Valide l'ensemble des docs IS (SFD+ICD+REQ+DVP) vs le Product Brief."""
        ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
        if not ecr:
            raise ValueError(f"ECR {ecr_number} introuvable")

        # Récupérer tous les docs IS
        all_docs = (
            session.query(EngineeringDocument)
            .filter(
                EngineeringDocument.ecr_id == ecr.id,
                EngineeringDocument.doc_type.in_(["product_brief", "sfd", "icd", "arbitrage", "req", "dvp"]),
            )
            .order_by(EngineeringDocument.doc_type, EngineeringDocument.is_domain)
            .all()
        )

        if not all_docs:
            raise ValueError(f"Aucun document trouvé pour {ecr_number}")

        docs_by_type: dict[str, list] = {}
        for d in all_docs:
            docs_by_type.setdefault(d.doc_type, []).append({
                "doc_number": d.doc_number,
                "is_domain": d.is_domain,
                "content": json.loads(d.content) if d.content else {},
            })

        user_prompt = (
            f"ECR : {ecr_number} — {ecr.title}\n\n"
            f"Documents à valider :\n"
            f"{json.dumps(docs_by_type, ensure_ascii=False, indent=2)}"
        )

        result = self._call_claude(
            system=_REVIEW_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=3000,
        )
        if not result:
            return None

        doc_number = f"DR-{ecr_number}"
        existing = session.query(EngineeringDocument).filter_by(doc_number=doc_number).first()
        if existing:
            doc_number = f"DR-{ecr_number}-v{existing.version + 1}"

        doc = self._save_doc(
            session,
            doc_number=doc_number,
            doc_type="design_review",
            ecr_id=ecr.id,
            is_domain=None,
            title=f"Design Review — {ecr_number}",
            content=json.dumps(result, ensure_ascii=False),
        )
        self._log.info("AP — Design Review produit", extra={"doc": doc_number, "decision": result.get("overall_decision")})
        return doc

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _call_claude(self, system: str, user_prompt: str, max_tokens: int = _MAX_TOKENS) -> dict | None:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=_TEMPERATURE,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()
        except Exception as exc:
            self._log.error("AP — appel Claude échoué", extra={"error": str(exc)})
            return None

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end]) if start != -1 else None
        except Exception as exc:
            self._log.error("AP — parsing JSON échoué", extra={"error": str(exc), "raw": raw[:300]})
            return None

    def _next_doc_number(self, session: Session, prefix: str) -> str:
        last = (
            session.query(EngineeringDocument.doc_number)
            .filter(EngineeringDocument.doc_number.like(f"{prefix}-%"))
            .order_by(EngineeringDocument.id.desc())
            .first()
        )
        if last:
            try:
                n = int(last[0].split("-")[1]) + 1
            except Exception:
                n = 1
        else:
            n = 1
        return f"{prefix}-{n:03d}"

    def _save_doc(
        self,
        session: Session,
        doc_number: str,
        doc_type: str,
        ecr_id: int | None,
        is_domain: str | None,
        title: str,
        content: str,
        status: str = "soumis",
    ) -> EngineeringDocument:
        doc = EngineeringDocument(
            doc_number=doc_number,
            doc_type=doc_type,
            ecr_id=ecr_id,
            is_domain=is_domain,
            title=title,
            content=content,
            status=status,
        )
        session.add(doc)
        session.flush()
        return doc
