"""Builds every long-lived service once per process (no import-time side effects)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from subwise.agent.graph import AgentDeps
from subwise.config import Settings
from subwise.db.session import make_engine, make_session_factory
from subwise.llm.gateway import LLMGateway, OllamaGateway
from subwise.memory.backends import Checkpointer, Store
from subwise.memory.learned import LearnedMemory
from subwise.research.fetch import Fetcher
from subwise.research.search import get_search_provider
from subwise.services.prices import PriceService
from subwise.worker.events import EventSink
from subwise.worker.runner import RunWorker, sweep_orphaned_runs

log = logging.getLogger(__name__)
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def run_migrations(settings: Settings) -> None:
    """Bring app.db to the latest schema (idempotent)."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    fetcher: Fetcher
    prices: PriceService
    llm: LLMGateway
    store: Store
    memory: LearnedMemory
    events: EventSink
    checkpointer: Checkpointer
    worker: RunWorker

    def close(self) -> None:
        self.worker.shutdown()
        self.fetcher.close()
        self.checkpointer.close()
        self.store.close()
        self.engine.dispose()


def build_container(
    settings: Settings,
    *,
    llm: LLMGateway | None = None,
    fetcher: Fetcher | None = None,
    migrate: bool = True,
) -> Container:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if migrate:
        run_migrations(settings)
    engine = make_engine(settings)
    sf = make_session_factory(engine)
    fetcher = fetcher or Fetcher(
        sources_dir=settings.sources_dir, playwright_enabled=settings.playwright_enabled
    )
    prices = PriceService(sf, fetcher, get_search_provider(settings))
    prices.sync_registry()
    llm = llm or OllamaGateway(settings)
    store = Store(settings.memory_db_path)
    memory = LearnedMemory(store)
    events = EventSink(sf)
    checkpointer = Checkpointer(settings.checkpoints_db_path)
    deps = AgentDeps(
        settings=settings, session_factory=sf, prices=prices, llm=llm, memory=memory, events=events
    )
    worker = RunWorker(deps, checkpointer)
    lost = sweep_orphaned_runs(worker)
    if lost:
        log.warning("%d run(s) were interrupted by a restart and marked WORKER_LOST", lost)
    return Container(
        settings, engine, sf, fetcher, prices, llm, store, memory, events, checkpointer, worker
    )
