# gives each changed path a category from the ordered rules file, first match wins

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from GitHub_Connector.schemas import Category
from GitHub_Connector.settings import get_settings


@lru_cache
def _load(rules_file: Path) -> tuple[bytes, list[tuple[str, Category]], Category]:
    # reads the rules once per file, line endings normalised so a Windows checkout hashes the same
    raw = rules_file.read_bytes().replace(b"\r\n", b"\n")
    data = json.loads(raw)
    rules = [(r["pattern"], Category(r["category"])) for r in data.get("rules", [])]
    return raw, rules, Category(data["fallback"])


def config_version() -> str:
    # hashes the rules file, so any rule change shows up in every run file
    raw, _, _ = _load(get_settings().rules_file)
    return hashlib.sha256(raw).hexdigest()[:12]


def classify(path: str) -> Category:
    # returns the category of the first rule that matches, else the fallback
    _, rules, fallback = _load(get_settings().rules_file)
    for pattern, category in rules:
        if matches(pattern, path):
            return category
    return fallback


def matches(pattern: str, path: str) -> bool:
    # matches one rule pattern against a repo-relative path
    raise NotImplementedError("pattern rules arrive with ticket 07")
