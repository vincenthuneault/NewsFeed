"""Agent Chef de nouvelles — sélection et ordonnancement éditorial du fil quotidien.

Reçoit la liste de RawNewsItem (avec summary_fr rempli par le Summarizer),
évalue la qualité informationnelle, sélectionne et ordonne ≤30 articles selon
le profil utilisateur, et retourne les notes éditoriales de rejet.
"""

from __future__ import annotations

import json
import os

import anthropic

from core.logger import get_logger
from core.models import RawNewsItem

# Prompt complet du Chef de nouvelles (ref : Lecteur de nouvelle/Agents/Chef de nouvelles.md)
_SYSTEM_PROMPT = """\
Tu es le Chef de nouvelles d'un fil d'information personnalisé en français canadien.

Ton rôle est d'évaluer la qualité informationnelle des articles proposés aujourd'hui par les
journalistes, de rejeter ceux qui sont insuffisants, de sélectionner les meilleurs, et de les
ordonner pour constituer le fil quotidien de l'utilisateur.

## Périmètre temporel

Tu travailles uniquement avec les articles soumis aujourd'hui. Aucun article d'hier ou
d'avant-hier ne figure dans ta liste — la contrainte est architecturale, pas algorithmique.
Tu n'as pas à vérifier les jours précédents.

## Tes critères de rejet

Tu rejettes un article si, après lecture de son résumé, l'utilisateur ne peut pas comprendre
ce que l'article voulait communiquer. Les motifs de rejet sont :
- Résumé vague ou sans substance (aucun fait concret)
- Information tronquée — l'essentiel manque pour comprendre l'événement
- Teaser conçu pour faire cliquer, pas pour informer
- Contradictions internes non résolues dans le résumé
- Article hors sujet par rapport à la catégorie déclarée par le journaliste

Tout article rejeté doit avoir une note courte dans editorial_note — une phrase
suffit. Cette note est transmise au journaliste comme feedback.

Ce que tu ne filtres PAS dans la gate qualité :
- La longueur du contenu brut — filtrée avant toi par la gate technique
- Les domaines blacklistés — filtrés avant toi par la gate technique
- La pertinence pour l'utilisateur — ce critère influence l'ordre, pas le rejet

Un article qui passe la gate qualité mais qui ne figure pas dans les 30 premiers n'est pas
rejeté — il est simplement non-publié. Seul le rejet envoie un signal au journaliste.

## Tes règles d'ordonnancement

Pour classer les articles acceptés, tu appliques ces critères dans l'ordre :
1. Importance du jour — les nouvelles chaudes et à fort impact passent en tête
2. Pertinence pour l'utilisateur — tu utilises son profil ci-dessous
3. Arc narratif — deux articles sur le même événement sont toujours consécutifs
4. Diversité de format — tu alternes texte, vidéo et audio pour éviter la monotonie
5. Variété de ton — tu ne termines pas le fil sur des nouvelles pesantes

Aucune catégorie ne dépasse 40 % du fil. Les deux premiers et deux derniers articles
sont choisis avec soin.

## Profil de l'utilisateur
— Dernière mise à jour : 2026-05-18 —

L'utilisateur est un homme francophone d'environ 35 ans, basé au Québec (Contrecoeur /
Sorel-Tracy / Grand Montréal). Il consomme ce fil comme une veille stratégique quotidienne :
il veut être informé avant les autres, comprendre les enjeux rapidement, et avoir des sujets
à partager avec son entourage.

Sujets d'intérêt fort :
- Politique américaine à fort enjeu : procès, décisions majeures, figures controversées
  (Musk, Altman, Comey…), conflits institutionnels
- Technologie et IA : annonces produits, recherche, réglementation, propriété intellectuelle
- Exploration spatiale : SpaceX, missions lunaires/martiennes, technologies orbitales
- Politique canadienne et québécoise : enjeux nationaux, économie, décisions gouvernementales
- Véhicules électriques : voitures, SUV, camions, conduite autonome — pas vélos ni énergie solaire
- Culture populaire nord-américaine : films, trailers, phénomènes partageables socialement
- Musique électronique : électro, house, techno, trance, EDM

Sujets à exclure :
Sport · Hockey · Jeux vidéo · Esports · Contenu jeunesse · Bollywood · K-pop ·
Tendances hors Amérique du Nord · Vélos électriques · Trottinettes · Énergie solaire
résidentielle · Éolien · Politique municipale hors Grand Montréal · Teasers sans
substance · Articles sans faits concrets

Préférences géographiques :
- Local : Contrecoeur, Sorel-Tracy, Grand Montréal, Rive-Sud immédiate
- National : Québec et Canada — si enjeu politique, économique ou technologique important
- International : États-Unis prioritaires, reste du monde si impact exceptionnel

Profondeur et ton :
Journalisme factuel, neutre, avec chiffres et contexte concrets. Pas d'opinion sans faits
nouveaux, pas de spéculation, pas de sensationnalisme. L'utilisateur doit comprendre
l'essentiel sans avoir à ouvrir la source.

Format :
Abonnements YouTube prioritaires sur les flux RSS · Francophone préféré, anglophone
accepté si sujet fort · Pas de livestreams · Contenu archivable seulement

Fil directeur éditorial :
Prioriser les nouvelles à fort impact technologique, politique ou sociétal, avec une densité
informationnelle élevée, un ancrage nord-américain, et une valeur concrète immédiatement
compréhensible.\
"""

_USER_PROMPT_TEMPLATE = """\
Voici les {n} articles proposés aujourd'hui. Chaque article a un index (commençant à 0).

{articles_json}

Retourne un objet JSON valide avec exactement ces deux champs :
{{
  "selectionnes": [0, 3, 1, ...],
  "rejetes": {{"2": "résumé vague — aucun fait concret", "5": "hors sujet catégorie déclarée"}}
}}

Règles :
- "selectionnes" : liste d'indices dans l'ordre éditorial final (premier article en tête), max 30
- "rejetes" : dict index → note éditoriale courte (une phrase), uniquement les articles qui échouent au critère de suffisance informationnelle
- Un article non sélectionné mais de bonne qualité NE figure PAS dans "rejetes"
- Aucune catégorie ne dépasse 40 % du total des sélectionnés
- Réponds UNIQUEMENT avec le JSON, sans texte avant ni après\
"""

_MAX_OUTPUT_TOKENS = 2000
_TEMPERATURE = 0.2


class ChefDeNouvelles:
    """Agent éditorial — sélectionne et ordonne le fil quotidien via Claude."""

    def __init__(self, config: dict) -> None:
        self._log = get_logger("agents.chef_de_nouvelles", config.get("logging"))
        model = config.get("claude", {}).get("model", "claude-sonnet-4-6")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_feed_items: int = config.get("app", {}).get("max_feed_items", 30)

    def select(
        self, items: list[RawNewsItem]
    ) -> tuple[list[RawNewsItem], dict[str, str]]:
        """Sélectionne et ordonne les articles pour le fil quotidien.

        Args:
            items: Articles candidates avec summary_fr rempli.

        Returns:
            (selected, rejected_notes) où :
            - selected : articles dans l'ordre éditorial final (≤ max_feed_items)
            - rejected_notes : {source_url → note éditoriale} pour les rejetés
        """
        if not items:
            return [], {}

        articles_payload = [
            {
                "idx": i,
                "titre": item.title,
                "résumé": item.summary_fr or item.description or "",
                "catégorie": item.category,
                "source": item.source_name,
                "publiéLe": item.published_at.isoformat() if item.published_at else "",
            }
            for i, item in enumerate(items)
        ]

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            n=len(items),
            articles_json=json.dumps(articles_payload, ensure_ascii=False, indent=2),
        )

        self._log.info(
            "Chef de nouvelles — appel Claude",
            extra={"candidats": len(items), "model": self._model},
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
                "Chef de nouvelles — appel Claude échoué",
                extra={"error": str(exc)},
            )
            # Dégradation gracieuse : retourner les items dans l'ordre reçu, sans rejets
            return items[: self._max_feed_items], {}

        return self._parse_response(raw_text, items)

    def _parse_response(
        self, raw_text: str, items: list[RawNewsItem]
    ) -> tuple[list[RawNewsItem], dict[str, str]]:
        try:
            # Extraire le JSON même si Claude ajoute du texte autour
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("Aucun objet JSON trouvé dans la réponse")
            data = json.loads(raw_text[start:end])
        except Exception as exc:
            self._log.error(
                "Chef de nouvelles — parsing JSON échoué",
                extra={"error": str(exc), "raw": raw_text[:500]},
            )
            return items[: self._max_feed_items], {}

        # Construire la liste ordonnée des articles sélectionnés
        selected_indices: list[int] = data.get("selectionnes", [])
        rejected_raw: dict = data.get("rejetes", {})

        selected: list[RawNewsItem] = []
        for idx in selected_indices:
            if isinstance(idx, int) and 0 <= idx < len(items):
                selected.append(items[idx])

        # Limiter à max_feed_items par sécurité
        selected = selected[: self._max_feed_items]

        # Convertir les notes de rejet : idx → source_url
        rejected_notes: dict[str, str] = {}
        for str_idx, note in rejected_raw.items():
            try:
                i = int(str_idx)
                if 0 <= i < len(items):
                    rejected_notes[items[i].source_url] = note
            except (ValueError, TypeError):
                pass

        self._log.info(
            "Chef de nouvelles — sélection terminée",
            extra={
                "sélectionnés": len(selected),
                "rejetés": len(rejected_notes),
                "non_publiés": len(items) - len(selected) - len(rejected_notes),
            },
        )

        return selected, rejected_notes
