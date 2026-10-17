# runs one analysis end to end, callable without HTTP by the API, a later Action or the webhook

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from GitHub_Connector import rules, runs
from GitHub_Connector.fetch import fetch
from GitHub_Connector.schemas import AnalysisRequest, AnalysisResult, Change, Status
from GitHub_Connector.settings import get_settings


def analyze(request: AnalysisRequest) -> AnalysisResult:
    # compares head against base, classifies each change, saves the run file once
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
        skipped=[],
        created_at=_now(),
    )
    runs.save(result.analysis_id, runs.dump(result))
    return result


def _now() -> str:
    # formats the current time as ISO 8601 UTC with milliseconds and a Z
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
