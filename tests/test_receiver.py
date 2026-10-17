# covers signature handling, dedupe and the ref-update edge cases

from conftest import post, push_body, sign


# --- signature ------------------------------------------------------

def test_valid_signature_is_accepted(client):
    assert post(client, push_body()).status_code == 200


def test_tampered_body_is_rejected(client):
    body = push_body()
    good = sign(body)
    # flips one byte after signing, the digest must no longer match
    tampered = body.replace(b"hello-world", b"hello-w0rld")
    r = client.post(
        "/hooks/github",
        content=tampered,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "d-1",
            "X-Hub-Signature-256": good,
        },
    )
    assert r.status_code == 403


def test_missing_signature_header_is_rejected(client):
    r = client.post(
        "/hooks/github",
        content=push_body(),
        headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "d-1"},
    )
    assert r.status_code == 403


def test_wrong_secret_is_rejected(client):
    body = push_body()
    assert post(client, body, signature=sign(body, "not-the-secret")).status_code == 403


# --- dedupe ---------------------------------------------------------

def test_replayed_delivery_is_stored_once(client):
    from GitHub_Connector import store

    body = push_body()
    first = post(client, body, delivery="same-id")
    second = post(client, body, delivery="same-id")

    assert first.status_code == 200
    # stays 200 so Redeliver in the GitHub UI shows green
    assert second.status_code == 200
    assert store.count_events() == 1


def test_distinct_deliveries_are_both_stored(client):
    from GitHub_Connector import store

    post(client, push_body(), delivery="d-1")
    post(client, push_body(), delivery="d-2")
    assert store.count_events() == 2


# --- event routing --------------------------------------------------

def test_ping_is_acknowledged(client):
    from GitHub_Connector import store

    r = post(client, b"{}", event="ping")
    assert r.status_code == 200
    assert store.count_events() == 0


def test_unhandled_event_is_ignored(client):
    from GitHub_Connector import store

    r = post(client, push_body(), event="pull_request")
    assert r.status_code == 204
    assert store.count_events() == 0


def test_malformed_json_is_rejected(client):
    assert post(client, b"not json at all").status_code == 400


def test_payload_without_repository_is_rejected(client):
    assert post(client, b'{"ref": "refs/heads/main"}').status_code == 400


# --- ref-update edge cases -----------------------------------------

def test_commit_pair_is_recorded(client):
    from GitHub_Connector import store

    post(client, push_body(), delivery="d-1")
    row = store.get_by_delivery_id("d-1")
    assert row.before == "a" * 40
    assert row.after == "b" * 40
    assert row.repo_full_name == "octocat/hello-world"
    assert row.ref == "refs/heads/main"


def test_branch_create_has_no_base(client):
    from GitHub_Connector import store

    # GitHub sends 40 zeros as before when a push creates the branch
    body = push_body(before="0" * 40, created=True)
    post(client, body, delivery="create")

    row = store.get_by_delivery_id("create")
    assert row.before is None
    assert row.created is True
    assert row.after == "b" * 40


def test_branch_delete_has_no_head(client):
    from GitHub_Connector import store

    body = push_body(after="0" * 40, deleted=True, head_commit=None)
    post(client, body, delivery="delete")

    row = store.get_by_delivery_id("delete")
    assert row.after is None
    assert row.deleted is True
    assert row.head_commit_id is None


def test_force_push_is_flagged(client):
    from GitHub_Connector import store

    post(client, push_body(forced=True), delivery="forced")
    assert store.get_by_delivery_id("forced").forced is True


def test_raw_payload_is_kept_for_replay(client):
    import json

    from GitHub_Connector import store

    body = push_body()
    post(client, body, delivery="d-1")
    assert json.loads(store.get_by_delivery_id("d-1").raw_payload) == json.loads(body)


# --- parse unit -----------------------------------------------------

def test_branch_create_push_has_no_before():
    from GitHub_Connector.parse import parse

    event = parse(push_body(before="0" * 40, created=True), "d-1")
    assert event.has_before is False
    assert event.is_analyzable is True


def test_push_event_not_analyzable_after_delete():
    from GitHub_Connector.parse import parse

    event = parse(push_body(after="0" * 40, deleted=True), "d-1")
    assert event.is_analyzable is False
