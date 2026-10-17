# saves and loads run files by analysis_id, the one place v3 swaps for a durable store

from __future__ import annotations

import json
import os
from pathlib import Path

from GitHub_Connector.schemas import AnalysisResult
from GitHub_Connector.settings import get_settings


def dump(result: AnalysisResult) -> bytes:
    # serialises a result, the only serializer, so POST and GET bytes always agree
    return json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _path(analysis_id: str) -> Path:
    # places a run file inside the run store folder
    return get_settings().runs_dir / f"{analysis_id}.json"


def save(analysis_id: str, data: bytes) -> None:
    # writes one run file once, via a temp file so a reader never sees half a run
    folder = get_settings().runs_dir
    folder.mkdir(parents=True, exist_ok=True)
    final = _path(analysis_id)
    if final.exists():
        raise FileExistsError(f"run {analysis_id} already saved")
    tmp = folder / f".{analysis_id}.tmp"
    try:
        tmp.write_bytes(data)
        os.replace(tmp, final)
    finally:
        tmp.unlink(missing_ok=True)


def load(analysis_id: str) -> bytes | None:
    # returns a run file's original bytes, None when there is no such run
    path = _path(analysis_id)
    return path.read_bytes() if path.is_file() else None
