# receives GitHub webhook deliveries, verifies them, records the commit pair

from __future__ import annotations

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Header, HTTPException, Request, Response

from GitHub_Connector import store
from GitHub_Connector.config import get_settings
from GitHub_Connector.parse import InvalidPayload, parse

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # opens the event store before the first delivery lands
    store.init_db()
    yield


app = FastAPI(title="DocumentationDrifter webhook receiver", lifespan=lifespan)


def verify_signature(body: bytes, secret: str, signature_header: str | None) -> bool:
    # checks the HMAC GitHub sent, over the exact bytes it sent

    if not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256
    ).hexdigest()

    # compares in constant time, a plain == leaks the digest one byte at a time
    return hmac.compare_digest(expected, signature_header)


@app.get("/health")
def health() -> dict[str, str]:
    # reports liveness, handy once this is deployed behind something
    return {"status": "ok"}


@app.post("/hooks/github")
async def receive(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    # handles one delivery, answering well inside GitHub's 10 second timeout

    # reads raw bytes first, re-serialising parsed JSON would change the digest
    body = await request.body()

    secret = get_settings().webhook_secret
    if not secret:
        # fails closed, an unset secret must never mean "accept anything"
        log.error("webhook_secret is not configured")
        raise HTTPException(status_code=500, detail="Receiver is not configured")

    if not verify_signature(body, secret, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Signature did not match")

    if not x_github_delivery:
        raise HTTPException(status_code=400, detail="X-GitHub-Delivery is missing")

    # answers the hook's setup probe, GitHub sends this the moment you save it
    if x_github_event == "ping":
        return Response(status_code=200, content="pong")

    if x_github_event != "push":
        # ignores the rest on purpose, PR and install events land in a later slice
        return Response(status_code=204)

    try:
        event = parse(body, x_github_delivery)
    except InvalidPayload as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = store.save_push(event)
    if not stored:
        # treats a replay as success, so Redeliver in the GitHub UI stays green
        log.info("duplicate delivery %s ignored", event.delivery_id)
        return Response(status_code=200, content="duplicate")

    log.info(
        "stored %s %s %s..%s",
        event.delivery_id,
        event.repo_full_name,
        (event.before or "none")[:7],
        (event.after or "none")[:7],
    )
    return Response(status_code=200, content="ok")
