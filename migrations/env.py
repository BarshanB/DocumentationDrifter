"""Alembic environment.

This file is the bridge between Alembic and our code. Two jobs:

  1. tell Alembic where the database is (from our Settings, not alembic.ini)
  2. tell Alembic what the schema SHOULD look like (Base.metadata)

With (2) wired up, `alembic revision --autogenerate -m "..."` compares the
live database against our models and writes the migration for us.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from GitHub_Connector.config import get_settings
from GitHub_Connector.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injected at runtime so the URL lives in one place (our Settings) instead of
# being duplicated into a committed .ini file.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# How Alembic knows what the schema should be. Importing models above is what
# populates this -- a model in a file nobody imports is invisible to
# autogenerate, which is the usual cause of "my new table wasn't detected".
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it.

    Useful when a DBA must review changes before they touch production.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect and apply migrations for real."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # one short-lived connection; no pool needed
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Without this, autogenerate ignores type changes (String(40) ->
            # String(64) would be silently skipped).
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
