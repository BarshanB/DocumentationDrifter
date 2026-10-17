# runs one analysis end to end, callable without HTTP by the API, a later Action or the webhook

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from GitHub_Connector import rules, runs
from GitHub_Connector.fetch import fetch
from GitHub_Connector.schemas import (
    AnalysisError,
    AnalysisRequest,
    AnalysisResult,
    Change,
    ErrorCode,
    Skipped,
    Status,
)
from GitHub_Connector.settings import get_settings

# matches owner/name as GitHub allows it, checked before any network call
REPOSITORY = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")


def validate(request: AnalysisRequest) -> None:
    # rejects malformed input with INVALID_REQUEST, so garbage never reaches git
    def invalid(message: str) -> AnalysisError:
        return AnalysisError(ErrorCode.INVALID_REQUEST, message)

    if not REPOSITORY.match(request.repository):
        raise invalid("repository must be in owner/name format")
    if not SHA.match(request.commit_id):
        raise invalid("commit_id must be 7 to 40 hexadecimal characters")
    if request.base_commit is not None and not SHA.match(request.base_commit):
        raise invalid("base_commit must be 7 to 40 hexadecimal characters")


def analyze(request: AnalysisRequest) -> AnalysisResult:
    # compares head against base, classifies each change, saves the run file once
    validate(request)
    with fetch(request.repository, request.commit_id, request.base_commit) as cmp:
        changes = [
            Change(
                path=c.path,
                old_path=c.old_path,
                change_type=c.change_type,
                category=rules.classify(c.path),
            )
            for c in cmp.changes
        ]
        skipped = [Skipped(path=s.path, reason=s.reason) for s in cmp.skipped]
        head, base = cmp.head, cmp.base

    result = AnalysisResult(
        analysis_id="an-" + uuid.uuid4().hex,
        repository=request.repository,
        head_commit=head,
        base_commit=base,
        config_version=rules.config_version(),
        tool_version=get_settings().tool_version,
        status=Status.SUCCESS,
        error=None,
        issues=[],
        changes=sorted(changes, key=lambda c: c.path),
        skipped=sorted(skipped, key=lambda s: s.path),
        created_at=_now(),
    )
    runs.save(result.analysis_id, runs.dump(result))
    return result


def _now() -> str:
    # formats the current time as ISO 8601 UTC with milliseconds and a Z
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
