# holds v1 runtime settings, kept apart from v0's config so neither disturbs the other

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# anchors defaults to the repo, the app runs from Source/ so CWD cannot be trusted
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(__file__).resolve().parent


class AnalysisSettings(BaseSettings):
    # reads DRIFTER_* variables, ignores everything else in the environment
    model_config = SettingsConfigDict(env_prefix="DRIFTER_", extra="ignore")

    # resolves owner/name to <base><owner>/<name>.git, tests point it at local bare repos
    remote_base_url: str = "https://github.com/"

    # stores run files, wiped on redeploy and restart until v3 makes it durable
    runs_dir: Path = REPO_ROOT / "runs"

    # holds temporary clones, None means the system temp folder
    clone_dir: Path | None = None

    # lists the ordered path rules, config_version is a hash of this file
    rules_file: Path = PACKAGE_DIR / "path_rules.json"

    # skips any changed file over this many bytes
    max_file_bytes: int = 1024 * 1024

    # caps each git call and the whole analysis, both end in 500 TIMEOUT
    git_timeout: float = 60
    analysis_deadline: float = 120

    # runs at most this many analyses at once, extra requests wait for a slot
    max_concurrent: int = 2

    # names the build in every run file
    tool_version: str = "1.1.0"


@lru_cache
def get_settings() -> AnalysisSettings:
    # caches the settings, tests clear the cache after repointing the environment
    return AnalysisSettings()
