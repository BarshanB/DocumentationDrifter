# guards config discovery, the app runs from Source/ so CWD must not matter

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "Source"

# resolves settings in a clean process, the test fixtures preset env vars
PROBE = (
    "import sys; sys.path.insert(0, r'%s');"
    "from GitHub_Connector.config import get_settings, REPO_ROOT;"
    "s = get_settings();"
    "print(REPO_ROOT); print(s.webhook_secret); print(s.database_url)"
) % SOURCE


def _resolve_from(cwd: Path) -> list[str]:
    # runs the probe from a given directory, returns root/secret/db url
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("WEBHOOK_SECRET", "DATABASE_URL")
    }
    out = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip().splitlines()


def test_repo_root_is_found_from_any_cwd(tmp_path):
    # the three places you might plausibly launch from
    for cwd in (REPO_ROOT, SOURCE, tmp_path):
        root, _, db_url = _resolve_from(cwd)
        assert Path(root) == REPO_ROOT, f"wrong root when run from {cwd}"
        # the sqlite default must be absolute, or the db follows CWD around
        if db_url.startswith("sqlite"):
            assert ":////" in db_url, f"db path is CWD-relative when run from {cwd}"


def test_dotenv_is_read_when_running_from_source():
    # the real failure: uvicorn must run from Source/, .env lives at the root
    if not (REPO_ROOT / ".env").exists():
        import pytest

        pytest.skip("no .env present")

    from_root = _resolve_from(REPO_ROOT)[1]
    from_source = _resolve_from(SOURCE)[1]
    assert from_source == from_root
    assert from_source != "", "secret was not picked up from .env"
