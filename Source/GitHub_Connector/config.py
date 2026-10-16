# holds runtime settings, read once from the environment

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# anchors config to the repo, the app is run from Source/ so CWD cannot be trusted
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # reads the repo-root .env, ignores anything it does not declare
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # signs every delivery, must match the secret set on the GitHub webhook
    webhook_secret: str = ""

    # points at the event store, absolute so it lands beside .env not beside CWD
    database_url: str = f"sqlite:///{REPO_ROOT / 'drifter.db'}"


@lru_cache
def get_settings() -> Settings:
    # caches the settings, so the .env file is read once per process
    return Settings()
