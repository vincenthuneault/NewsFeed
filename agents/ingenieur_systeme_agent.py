"""Agent Ingénieur Système — produit SFD, ICD, REQ et DVP pour un ECR.

Deux opérations :
  run_draft()       — produit SFD + ICD (Round 1, avant arbitrage)
  run_completion()  — produit REQ + DVP (Round 2, après arbitrage ou mono-domaine)

Le runtime prompt de chaque IS est chargé dynamiquement depuis son fichier .md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
from sqlalchemy.orm import Session

from core.logger import get_logger
from core.models import ECR, EngineeringDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IS_DOMAIN_MAP = {
    "IS-1": {
        "name": "Agents & Collecte",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-Agents.md",
    },
    "IS-2": {
        "name": "Pipeline & Traitement",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-Pipeline.md",
    },
    "IS-3": {
        "name": "IA & Contenu",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-IA.md",
    },
    "IS-4": {
        "name": "Backend & Données",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-Backend.md",
    },
    "IS-5": {
        "name": "Frontend Mobile",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-Frontend.md",
    },
    "IS-6": {
        "name": "Infrastructure & Déploiement",
        "md": "Lecteur de nouvelle/Agents/Ingénieur-Infra.md",
    },
}

_SFD_ICD_SUFFIX = """
## Opération : SFD + ICD (Round 1 — Draft)

Produis le SFD et l'ICD pour le domaine qui t'est assigné.

Le SFD décrit COMMENT ton domaine fonctionnera après le fix (comportements, états, flux).
L'ICD définit les contrats d'interface avec les autres domaines (format, déclencheur, producteur, consommateur).

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "sfd": {
    "domain": "IS-6",
    "title": "Titre du SFD",
    "functional_description": "Description narrative du comportement attendu (3-5 paragraphes)",
    "behaviors": [
      {
        "trigger": "Ce qui déclenche ce comportement",
        "action": "Ce que le système fait",
        "outcome": "Résultat observable"
      }
    ],
    "proposed_interfaces": [
      {
        "with_domain": "IS-2",
        "direction": "IS-2→IS-6",
        "description": "Ce qui est échangé",
        "proposed_format": "Type et structure proposée"
      }
    ]
  },
  "icd": {
    "domain": "IS-6",
    "interfaces": [
      {
        "interface_id": "IFC-ECR017-IS6-001",
        "with_domain": "IS-2",
        "direction": "IS-2→IS-6",
        "description": "Description précise de l'interface",
        "data_format": "Format exact (JSON, signal bool, HTTP endpoint, etc.)",
        "trigger": "Quand cette interface est invoquée",
        "error_handling": "Comportement si l'interface échoue"
      }
    ]
  }
}
"""

_REQ_DVP_SUFFIX = """
## Opération : REQ + DVP (Round 2 — Complétion)

Tu reçois le Product Brief et la décision d'arbitrage (si applicable).
Produis les REQs système et le DVP pour ton domaine, en respectant les contrats d'interface définis.

Les REQs doivent être formels et testables.
Le DVP doit couvrir : cas nominal, cas limites, dégradé, régression.

Réponds UNIQUEMENT avec ce JSON (sans texte avant ni après) :
{
  "req": {
    "domain": "IS-6",
    "requirements": [
      {
        "req_id": "REQ-ECR017-IS6-001",
        "title": "Titre court",
        "condition": "Déclencheur ou état système",
        "acceptance_criteria": "Critère mesurable et vérifiable",
        "constraint": "Contrainte technique ou non-fonctionnelle",
        "interface_affected": "Fichier(s) ou endpoint(s) concerné(s)"
      }
    ]
  },
  "dvp": {
    "domain": "IS-6",
    "test_cases": [
      {
        "case_id": "DVP-ECR017-IS6-TC1",
        "description": "Description du cas de test",
        "type": "nominal | limite | degrade | regression",
        "preconditions": "État du système avant le test",
        "steps": ["Étape 1", "Étape 2"],
        "expected_result": "Résultat attendu observable",
        "related_req": "REQ-ECR017-IS6-001"
      }
    ],
    "success_criteria": "Définition globale du succès pour ce domaine"
  }
}
"""

_MAX_TOKENS = 3000
_TEMPERATURE = 0.2


class IngenieurSystemeAgent:
    """Produit la documentation système (SFD, ICD, REQ, DVP) pour un ECR et un domaine IS."""

    def __init__(self, config: dict) -> None:
        self._log = get_logger("agents.ingenieur_systeme", config.get("logging"))
        model = config.get("claude", {}).get("model", "claude-sonnet-4-6")
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    def run_draft(
        self,
        session: Session,
        ecr_number: str,
        is_domain: str,
    ) -> dict[str, EngineeringDocument]:
        """Produit SFD + ICD pour un IS (Round 1, avant arbitrage)."""
        ecr, pb_doc, arb_doc = self._load_context(session, ecr_number)
        is_prompt = self._load_is_prompt(is_domain)
        pb_content = json.loads(pb_doc.content)

        # Trouver la responsabilité assignée à ce domaine
        responsibility = ""
        for a in pb_content.get("is_assignments", []):
            if a.get("domain") == is_domain:
                responsibility = a.get("responsibility", "")
                break

        user_prompt = (
            f"ECR : {ecr_number} — {ecr.title}\n\n"
            f"Product Brief :\n{pb_doc.content}\n\n"
            f"Ta responsabilité sur cet ECR : {responsibility}\n\n"
            f"Produis le SFD et l'ICD pour ton domaine ({is_domain})."
        )

        result = self._call_claude(
            system=is_prompt + _SFD_ICD_SUFFIX,
            user_prompt=user_prompt,
        )
        if not result:
            return {}

        docs = {}
        for doc_type in ("sfd", "icd"):
            if doc_type in result:
                ecr_digits = ecr_number.replace("ECR-", "")
                is_digits = is_domain.replace("IS-", "")
                doc_number = f"{doc_type.upper()}-ECR{ecr_digits}-IS{is_digits}"
                doc = self._save_doc(
                    session,
                    doc_number=doc_number,
                    doc_type=doc_type,
                    ecr_id=ecr.id,
                    is_domain=is_domain,
                    title=result[doc_type].get("title", f"{doc_type.upper()} — {ecr_number} {is_domain}"),
                    content=json.dumps(result[doc_type], ensure_ascii=False),
                )
                docs[doc_type] = doc
                self._log.info(f"IS — {doc_type.upper()} créé", extra={"doc": doc_number})

        session.flush()
        return docs

    def run_completion(
        self,
        session: Session,
        ecr_number: str,
        is_domain: str,
    ) -> dict[str, EngineeringDocument]:
        """Produit REQ + DVP pour un IS (Round 2, après arbitrage ou mono-domaine)."""
        ecr, pb_doc, arb_doc = self._load_context(session, ecr_number)
        is_prompt = self._load_is_prompt(is_domain)

        # Récupérer les SFD/ICD existants pour ce domaine
        existing_sfd_icd = (
            session.query(EngineeringDocument)
            .filter(
                EngineeringDocument.ecr_id == ecr.id,
                EngineeringDocument.is_domain == is_domain,
                EngineeringDocument.doc_type.in_(["sfd", "icd"]),
            )
            .all()
        )
        sfd_icd_context = {d.doc_type: json.loads(d.content) for d in existing_sfd_icd}

        arb_context = f"\nDécision d'arbitrage :\n{arb_doc.content}\n" if arb_doc else ""

        user_prompt = (
            f"ECR : {ecr_number} — {ecr.title}\n\n"
            f"Product Brief :\n{pb_doc.content}\n"
            f"{arb_context}\n"
            f"Tes SFD et ICD (Round 1) :\n{json.dumps(sfd_icd_context, ensure_ascii=False, indent=2)}\n\n"
            f"Produis maintenant les REQs et le DVP pour ton domaine ({is_domain}), "
            f"en respectant les contrats d'interface définis."
        )

        result = self._call_claude(
            system=is_prompt + _REQ_DVP_SUFFIX,
            user_prompt=user_prompt,
        )
        if not result:
            return {}

        docs = {}
        for doc_type in ("req", "dvp"):
            if doc_type in result:
                ecr_digits = ecr_number.replace("ECR-", "")
                is_digits = is_domain.replace("IS-", "")
                doc_number = f"{doc_type.upper()}-ECR{ecr_digits}-IS{is_digits}"
                doc = self._save_doc(
                    session,
                    doc_number=doc_number,
                    doc_type=doc_type,
                    ecr_id=ecr.id,
                    is_domain=is_domain,
                    title=f"{doc_type.upper()} — {ecr_number} {is_domain}",
                    content=json.dumps(result[doc_type], ensure_ascii=False),
                )
                docs[doc_type] = doc
                self._log.info(f"IS — {doc_type.upper()} créé", extra={"doc": doc_number})

        session.flush()
        return docs

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _load_context(
        self, session: Session, ecr_number: str
    ) -> tuple[ECR, EngineeringDocument, EngineeringDocument | None]:
        ecr = session.query(ECR).filter_by(ecr_number=ecr_number).first()
        if not ecr:
            raise ValueError(f"ECR {ecr_number} introuvable")

        pb_doc = (
            session.query(EngineeringDocument)
            .filter_by(ecr_id=ecr.id, doc_type="product_brief")
            .order_by(EngineeringDocument.id.desc())
            .first()
        )
        if not pb_doc:
            raise ValueError(f"Aucun Product Brief pour {ecr_number} — lancez --brief d'abord")

        arb_doc = (
            session.query(EngineeringDocument)
            .filter_by(ecr_id=ecr.id, doc_type="arbitrage")
            .order_by(EngineeringDocument.id.desc())
            .first()
        )
        return ecr, pb_doc, arb_doc

    def _load_is_prompt(self, is_domain: str) -> str:
        """Charge le runtime prompt depuis le fichier .md du domaine IS."""
        if is_domain not in IS_DOMAIN_MAP:
            raise ValueError(f"Domaine inconnu : {is_domain}. Valides : {list(IS_DOMAIN_MAP)}")

        md_path = PROJECT_ROOT / IS_DOMAIN_MAP[is_domain]["md"]
        content = md_path.read_text(encoding="utf-8")

        marker = "⚙️ RUNTIME PROMPT"
        if marker in content:
            runtime_section = content.split(marker, 1)[1]
            # Extraire le contenu entre les ``` du bloc de code
            parts = runtime_section.split("```")
            if len(parts) >= 3:
                return parts[1].strip()

        return content  # fallback : tout le fichier

    def _call_claude(self, system: str, user_prompt: str) -> dict | None:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()
        except Exception as exc:
            self._log.error("IS — appel Claude échoué", extra={"error": str(exc)})
            return None

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end]) if start != -1 else None
        except Exception as exc:
            self._log.error("IS — parsing JSON échoué", extra={"error": str(exc), "raw": raw[:300]})
            return None

    def _save_doc(
        self,
        session: Session,
        doc_number: str,
        doc_type: str,
        ecr_id: int,
        is_domain: str,
        title: str,
        content: str,
    ) -> EngineeringDocument:
        # Idempotent : si le doc existe déjà, le mettre à jour
        existing = session.query(EngineeringDocument).filter_by(doc_number=doc_number).first()
        if existing:
            existing.content = content
            existing.title = title
            existing.status = "soumis"
            return existing

        doc = EngineeringDocument(
            doc_number=doc_number,
            doc_type=doc_type,
            ecr_id=ecr_id,
            is_domain=is_domain,
            title=title,
            content=content,
            status="soumis",
        )
        session.add(doc)
        return doc
