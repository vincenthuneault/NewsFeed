"""Agent Aftersales — triage scientifique des signaux utilisateur.

Lit les commentaires, feedbacks et rapports de bugs non traités depuis le dernier
cycle, applique la méthode scientifique en 5 étapes, et produit des Investigations
accompagnées d'ECRs ou de MCAs selon la conclusion.

Exécuté quotidiennement après la publication du DailyFeed.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import anthropic
from sqlalchemy.orm import Session

from core.logger import get_logger
from core.models import (
    BugReport,
    ECR,
    Investigation,
    MCA,
    NewsItem,
    NewsComment,
    Feedback,
    DailyFeed,
)

_SYSTEM_PROMPT = """\
Tu es l'agent Aftersales d'un système de fil d'information personnalisé.

Ton rôle : analyser les signaux utilisateur (commentaires, feedbacks, rapports de bugs)
avec la méthode scientifique pour décider si une action corrective est nécessaire.

## Méthode en 5 étapes

1. Réception & Observation : lire le signal brut et son contexte
2. Formulation d'hypothèse : transformer l'observation en hypothèse testable
3. Plan d'investigation : définir les données à collecter AVANT de les regarder
4. Collecte & Analyse : analyser les données selon le plan
5. Conclusion & Décision : une des quatre décisions possibles

## Décisions possibles

- journalisation : signal isolé, subjectif, ou hypothèse réfutée — aucune action
- mca : hypothèse confirmée + réglable par config/prompt sans modifier le code
- ecr : hypothèse confirmée + nécessite une modification de code
- business : tendance comportementale de fond — signal de direction produit

## Profil utilisateur (contexte d'interprétation)

Homme francophone, ~35 ans, Contrecoeur / Sorel-Tracy / Grand Montréal.
Intérêts forts : politique américaine, tech/IA, espace, politique canadienne/québécoise,
véhicules électriques (voitures), culture pop nord-américaine, musique électronique EDM.
À exclure : sport, jeux vidéo, contenu jeunesse, Bollywood, K-pop.
Ton attendu : factuel, neutre, avec chiffres et contexte concret.

## Format de réponse

Retourne un objet JSON avec cette structure :
{
  "decision": "journalisation|mca|ecr|business",
  "hypothesis": "Hypothèse testée",
  "data_plan": "Ce que tu as voulu vérifier",
  "data_collected": "Résumé des observations et données",
  "conclusion": "Conclusion en une phrase",
  "ecr": null ou {
    "title": "Titre court",
    "priority": "haute|normale|basse",
    "severity": "haute|normale|basse",
    "symptom": "Symptôme observé",
    "root_cause": "Cause racine",
    "proposed_fix": "Correction technique proposée"
  },
  "mca": null ou {
    "title": "Titre court du changement",
    "target_agent": "Agent ciblé",
    "description": "Changement précis à appliquer",
    "justification": "Données qui justifient ce changement"
  }
}

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après.\
"""

_MAX_OUTPUT_TOKENS = 1500
_TEMPERATURE = 0.2


class AftersalesAgent:
    """Triage scientifique des signaux utilisateur."""

    def __init__(self, config: dict) -> None:
        self._log = get_logger("agents.aftersales", config.get("logging"))
        model = config.get("claude", {}).get("model", "claude-sonnet-4-6")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def run(self, session: Session) -> dict:
        """Traite tous les signaux non investigués depuis le dernier cycle.

        Retourne un résumé : {investigations: N, ecrs: N, mcas: N}
        """
        summary = {"investigations": 0, "ecrs": 0, "mcas": 0}

        # Déterminer le timestamp du dernier cycle
        last_run = self._last_run_timestamp(session)

        signals = self._collect_signals(session, last_run)
        total = sum(len(v) for v in signals.values())

        if total == 0:
            self._log.info("Aftersales — aucun nouveau signal")
            return summary

        self._log.info(
            "Aftersales — signaux détectés",
            extra={
                "commentaires": len(signals["comments"]),
                "feedbacks": len(signals["feedbacks"]),
                "bugs": len(signals["bugs"]),
            },
        )

        # Traiter chaque signal individuellement
        for comment in signals["comments"]:
            result = self._process_signal(session, "comment", comment.id, self._format_comment(session, comment))
            self._record_result(session, result, "comment", comment.id, summary)

        for feedback in signals["feedbacks"]:
            if feedback.comment:  # Seulement les feedbacks avec commentaire texte
                result = self._process_signal(session, "feedback", feedback.id, self._format_feedback(session, feedback))
                self._record_result(session, result, "feedback", feedback.id, summary)

        for bug in signals["bugs"]:
            result = self._process_signal(session, "bug_report", bug.id, self._format_bug(bug))
            self._record_result(session, result, "bug_report", bug.id, summary)

        session.commit()

        self._log.info(
            "Aftersales terminé",
            extra=summary,
        )
        return summary

    def _last_run_timestamp(self, session: Session) -> datetime:
        """Retourne le timestamp de la dernière investigation complétée."""
        last = (
            session.query(Investigation.completed_at)
            .filter(Investigation.completed_at.isnot(None))
            .order_by(Investigation.completed_at.desc())
            .first()
        )
        if last and last[0]:
            return last[0]
        # Premier cycle : remonter 7 jours
        from datetime import timedelta
        return datetime.now(timezone.utc) - timedelta(days=7)

    def _collect_signals(self, session: Session, since: datetime) -> dict:
        """Collecte les signaux non traités depuis `since`."""
        # Commentaires
        comments = (
            session.query(NewsComment)
            .filter(NewsComment.created_at > since)
            .all()
        )

        # Feedbacks avec commentaire texte
        feedbacks = (
            session.query(Feedback)
            .filter(Feedback.created_at > since)
            .filter(Feedback.comment.isnot(None))
            .filter(Feedback.comment != "")
            .all()
        )

        # Rapports de bugs
        bugs = (
            session.query(BugReport)
            .filter(BugReport.created_at > since)
            .all()
        )

        return {"comments": comments, "feedbacks": feedbacks, "bugs": bugs}

    def _format_comment(self, session: Session, comment: NewsComment) -> str:
        article = session.query(NewsItem).filter_by(id=comment.news_item_id).first()
        context = {}
        if article:
            context = {
                "article_titre": article.title,
                "article_catégorie": article.category,
                "article_source": article.source_name,
                "article_résumé": article.summary_fr or "",
            }
        return json.dumps({
            "type": "commentaire_article",
            "id": comment.id,
            "texte": comment.body,
            "créé_le": comment.created_at.isoformat(),
            "contexte_article": context,
        }, ensure_ascii=False)

    def _format_feedback(self, session: Session, feedback: Feedback) -> str:
        article = session.query(NewsItem).filter_by(id=feedback.news_item_id).first()
        context = {}
        if article:
            context = {
                "article_titre": article.title,
                "article_catégorie": article.category,
                "article_source": article.source_name,
            }
        return json.dumps({
            "type": "feedback_utilisateur",
            "id": feedback.id,
            "action": feedback.action,
            "commentaire": feedback.comment,
            "créé_le": feedback.created_at.isoformat(),
            "contexte_article": context,
        }, ensure_ascii=False)

    def _format_bug(self, bug: BugReport) -> str:
        return json.dumps({
            "type": "rapport_de_bug",
            "id": bug.id,
            "description": bug.description,
            "contexte": bug.context,
            "créé_le": bug.created_at.isoformat(),
        }, ensure_ascii=False)

    def _process_signal(
        self, session: Session, trigger_type: str, trigger_id: int, signal_json: str
    ) -> dict | None:
        """Appelle Claude pour analyser un signal. Retourne le résultat parsé."""

        # Vérifier si déjà investigué
        existing = (
            session.query(Investigation)
            .filter_by(trigger_type=trigger_type, trigger_id=trigger_id)
            .first()
        )
        if existing:
            return None

        # Vérifier si le signal correspond à un ECR/MCA existant ouvert
        open_items = self._open_ecr_mca_summary(session)

        user_prompt = (
            f"Voici le signal à analyser :\n\n{signal_json}\n\n"
            f"ECRs et MCAs ouverts actuellement :\n{open_items}\n\n"
            "Si ce signal est clairement rattachable à un item ouvert, "
            "mentionne-le dans ta conclusion (decision='journalisation') avec la référence. "
            "Sinon, lance une investigation complète."
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_OUTPUT_TOKENS,
                temperature=_TEMPERATURE,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = response.content[0].text.strip()
        except Exception as exc:
            self._log.error(
                "Aftersales — appel Claude échoué",
                extra={"trigger": f"{trigger_type}#{trigger_id}", "error": str(exc)},
            )
            return None

        try:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            return json.loads(raw_text[start:end]) if start != -1 else None
        except Exception as exc:
            self._log.error(
                "Aftersales — parsing JSON échoué",
                extra={"error": str(exc), "raw": raw_text[:300]},
            )
            return None

    def _open_ecr_mca_summary(self, session: Session) -> str:
        ecrs = session.query(ECR).filter(ECR.status.in_(["a_transmettre", "en_cours"])).all()
        mcas = session.query(MCA).filter(MCA.status.in_(["a_appliquer", "en_attente"])).all()
        lines = [f"ECR: {e.ecr_number} — {e.title}" for e in ecrs]
        lines += [f"MCA: {m.mca_number} — {m.title}" for m in mcas]
        return "\n".join(lines) if lines else "Aucun ECR ou MCA ouvert."

    def _record_result(
        self,
        session: Session,
        result: dict | None,
        trigger_type: str,
        trigger_id: int,
        summary: dict,
    ) -> None:
        if result is None:
            return

        ecr_id = None
        mca_id = None
        now = datetime.now(timezone.utc)

        # Créer ECR si nécessaire
        if result.get("decision") == "ecr" and result.get("ecr"):
            ecr_data = result["ecr"]
            next_num = self._next_ecr_number(session)
            ecr = ECR(
                ecr_number=next_num,
                title=ecr_data.get("title", ""),
                status="a_transmettre",
                priority=ecr_data.get("priority", "normale"),
                severity=ecr_data.get("severity", "normale"),
                symptom=ecr_data.get("symptom"),
                root_cause=ecr_data.get("root_cause"),
                proposed_fix=ecr_data.get("proposed_fix"),
            )
            session.add(ecr)
            session.flush()
            ecr_id = ecr.id
            summary["ecrs"] += 1
            self._log.info("Aftersales — ECR créé", extra={"ecr": next_num})

        # Créer MCA si nécessaire
        elif result.get("decision") == "mca" and result.get("mca"):
            mca_data = result["mca"]
            next_num = self._next_mca_number(session)
            mca = MCA(
                mca_number=next_num,
                title=mca_data.get("title", ""),
                status="a_appliquer",
                target_agent=mca_data.get("target_agent"),
                description=mca_data.get("description"),
                justification=mca_data.get("justification"),
            )
            session.add(mca)
            session.flush()
            mca_id = mca.id
            summary["mcas"] += 1
            self._log.info("Aftersales — MCA créé", extra={"mca": next_num})

        # Toujours créer une Investigation
        investigation = Investigation(
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            hypothesis=result.get("hypothesis"),
            data_plan=result.get("data_plan"),
            data_collected=result.get("data_collected"),
            conclusion=result.get("conclusion"),
            decision=result.get("decision"),
            ecr_id=ecr_id,
            mca_id=mca_id,
            completed_at=now,
        )
        session.add(investigation)
        summary["investigations"] += 1

    def _next_ecr_number(self, session: Session) -> str:
        last = (
            session.query(ECR.ecr_number)
            .order_by(ECR.id.desc())
            .first()
        )
        if last:
            try:
                n = int(last[0].split("-")[1]) + 1
            except Exception:
                n = 1
        else:
            n = 1
        return f"ECR-{n:03d}"

    def _next_mca_number(self, session: Session) -> str:
        last = (
            session.query(MCA.mca_number)
            .order_by(MCA.id.desc())
            .first()
        )
        if last:
            try:
                n = int(last[0].split("-")[1]) + 1
            except Exception:
                n = 1
        else:
            n = 1
        return f"MCA-{n:03d}"
