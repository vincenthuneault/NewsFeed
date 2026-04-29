"""Orchestrateur — lance tous les agents en parallèle et agrège les résultats."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.logger import get_logger
from core.models import AgentRun, RawNewsItem, get_session, init_db

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent

_AGENT_TIMEOUT = 300  # 5 min par agent


@dataclass
class AgentReport:
    agent_name: str
    status: str          # success | partial | failed
    items_collected: int = 0
    duration_seconds: float = 0.0
    error_message: str | None = None


class Orchestrator:
    """Lance les agents en parallèle et retourne les items agrégés."""

    def __init__(self, agents: list["BaseAgent"], config: dict) -> None:
        self._agents = agents
        self._config = config
        self._log = get_logger("core.orchestrator", config.get("logging"))
        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        self._session_factory = init_db(db_url)

    def run(self) -> tuple[list[RawNewsItem], list[AgentReport]]:
        """Exécute tous les agents en parallèle.

        Returns:
            Tuple (items agrégés, rapports par agent).
        """
        self._log.info(
            "Orchestrateur démarré",
            extra={"agents": [a.name for a in self._agents]},
        )

        all_items: list[RawNewsItem] = []
        reports: list[AgentReport] = []

        import time

        with ThreadPoolExecutor(max_workers=len(self._agents)) as executor:
            future_to_agent = {
                executor.submit(self._run_agent, agent): agent
                for agent in self._agents
            }

            for future in as_completed(future_to_agent, timeout=_AGENT_TIMEOUT + 10):
                agent = future_to_agent[future]
                try:
                    items, report = future.result(timeout=1)
                    all_items.extend(items)
                    reports.append(report)
                except TimeoutError:
                    report = AgentReport(
                        agent_name=agent.name,
                        status="failed",
                        error_message="Timeout dépassé",
                    )
                    reports.append(report)
                    self._log.error(
                        "Agent timeout", extra={"agent": agent.name}
                    )
                except Exception as exc:
                    report = AgentReport(
                        agent_name=agent.name,
                        status="failed",
                        error_message=str(exc),
                    )
                    reports.append(report)
                    self._log.error(
                        "Agent échoué",
                        extra={"agent": agent.name, "error": str(exc)},
                    )

        self._save_reports(reports)

        success = sum(1 for r in reports if r.status == "success")
        total = len(reports)
        self._log.info(
            "Orchestrateur terminé",
            extra={"agents_ok": success, "agents_total": total, "items": len(all_items)},
        )
        return all_items, reports

    def _run_agent(self, agent: "BaseAgent") -> tuple[list[RawNewsItem], AgentReport]:
        import time

        t0 = time.time()
        try:
            items = agent.collect()
            duration = time.time() - t0
            report = AgentReport(
                agent_name=agent.name,
                status="success",
                items_collected=len(items),
                duration_seconds=duration,
            )
            self._log.info(
                "Agent terminé",
                extra={"agent": agent.name, "items": len(items), "duration": f"{duration:.1f}s"},
            )
            return items, report
        except Exception as exc:
            duration = time.time() - t0
            self._log.error(
                "Agent erreur",
                extra={"agent": agent.name, "error": str(exc), "duration": f"{duration:.1f}s"},
            )
            raise

    def _save_reports(self, reports: list[AgentReport]) -> None:
        session = get_session(self._session_factory)
        try:
            for report in reports:
                session.add(
                    AgentRun(
                        agent_name=report.agent_name,
                        status=report.status,
                        items_collected=report.items_collected,
                        duration_seconds=report.duration_seconds,
                        error_message=report.error_message,
                    )
                )
            session.commit()
        except Exception as exc:
            session.rollback()
            self._log.error("Erreur sauvegarde rapports", extra={"error": str(exc)})
        finally:
            session.close()
