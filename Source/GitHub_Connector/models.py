# declares the event store tables

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # anchors the metadata, Alembic autogenerate reads this
    pass


class DeliveryEvent(Base):
    # records one accepted webhook delivery, one row per X-GitHub-Delivery

    __tablename__ = "delivery_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # dedupes replays, GitHub reuses this id when you hit Redeliver
    delivery_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    event: Mapped[str] = mapped_column(String(32), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)

    # carries the commit pair, the only thing the analyzer actually needs
    before: Mapped[str | None] = mapped_column(String(40), nullable=True)
    after: Mapped[str | None] = mapped_column(String(40), nullable=True)

    created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    head_commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # keeps the raw body, lets a later slice replay without asking GitHub again
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DeliveryEvent {self.delivery_id} {self.repo_full_name} "
            f"{(self.before or '')[:7]}..{(self.after or '')[:7]}>"
        )
