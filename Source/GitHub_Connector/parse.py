# turns a raw push payload into the commit pair the analyzer needs

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

# marks an absent commit, GitHub sends 40 zeros on branch create and delete
NULL_SHA = "0" * 40


class InvalidPayload(ValueError):
    # signals a body that is not a push we can act on
    pass


@dataclass(frozen=True)
class PushEvent:
    # carries one ref update, everything else is rebuilt from git later

    delivery_id: str
    repo_full_name: str
    ref: str
    before: str | None
    after: str | None
    created: bool
    deleted: bool
    forced: bool
    head_commit_id: str | None
    received_at: datetime
    raw_payload: str

    @property
    def is_analyzable(self) -> bool:
        # reports whether a head commit exists to snapshot, false once a branch is gone
        return self.after is not None

    @property
    def needs_base_snapshot(self) -> bool:
        # reports whether a base exists, false means first audit per the schema
        return self.before is not None


def _sha_or_none(value: object) -> str | None:
    # normalises a SHA, collapsing the all-zero placeholder to None
    if not isinstance(value, str) or value == NULL_SHA or not value.strip():
        return None
    return value


def parse(body: bytes, delivery_id: str) -> PushEvent:
    # accepts the raw body from the GitHub hook, returns the parsed push

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidPayload(f"body is not JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise InvalidPayload("payload is not an object")

    repo = payload.get("repository")
    if not isinstance(repo, dict) or not repo.get("full_name"):
        raise InvalidPayload("payload has no repository.full_name")

    ref = payload.get("ref")
    if not isinstance(ref, str) or not ref:
        raise InvalidPayload("payload has no ref")

    head_commit = payload.get("head_commit")
    head_commit_id = (
        _sha_or_none(head_commit.get("id")) if isinstance(head_commit, dict) else None
    )

    return PushEvent(
        delivery_id=delivery_id,
        repo_full_name=repo["full_name"],
        ref=ref,
        before=_sha_or_none(payload.get("before")),
        after=_sha_or_none(payload.get("after")),
        created=bool(payload.get("created")),
        deleted=bool(payload.get("deleted")),
        forced=bool(payload.get("forced")),
        head_commit_id=head_commit_id,
        received_at=datetime.now(timezone.utc),
        raw_payload=body.decode("utf-8", errors="replace"),
    )
