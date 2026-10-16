# persists accepted deliveries, deduped by GitHub's delivery id

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from GitHub_Connector.config import get_settings
from GitHub_Connector.models import Base, DeliveryEvent
from GitHub_Connector.parse import PushEvent

_engine = None
_Session: sessionmaker[Session] | None = None


def init_db(database_url: str | None = None) -> None:
    # opens the engine and creates the tables, called once at startup

    global _engine, _Session

    url = database_url or get_settings().database_url
    # keeps SQLite usable from the threadpool FastAPI runs sync handlers on
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    _engine = create_engine(url, connect_args=connect_args, future=True)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    # hands out a session, failing loudly if startup was skipped
    if _Session is None:
        raise RuntimeError("store.init_db() was never called")
    return _Session()


def save_push(event: PushEvent) -> bool:
    # stores one push, returns False when the delivery was already recorded

    with get_session() as session:
        row = DeliveryEvent(
            delivery_id=event.delivery_id,
            event="push",
            repo_full_name=event.repo_full_name,
            ref=event.ref,
            before=event.before,
            after=event.after,
            created=event.created,
            deleted=event.deleted,
            forced=event.forced,
            head_commit_id=event.head_commit_id,
            received_at=event.received_at,
            raw_payload=event.raw_payload,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # absorbs a replay, the unique delivery_id is what makes redelivery safe
            session.rollback()
            return False
        return True


def get_by_delivery_id(delivery_id: str) -> DeliveryEvent | None:
    # looks up one delivery, used by the tests and by manual inspection
    with get_session() as session:
        return session.scalar(
            select(DeliveryEvent).where(DeliveryEvent.delivery_id == delivery_id)
        )


def count_events() -> int:
    # counts stored deliveries, used by the tests
    with get_session() as session:
        return len(list(session.scalars(select(DeliveryEvent))))
