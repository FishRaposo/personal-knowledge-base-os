import sys
from logging.config import fileConfig
from pathlib import Path

from shared_core.database import Base
from sqlalchemy import create_engine

from alembic import context

# The Python package root for this project is apps/api/src (loose modules), so we
# import models the same way the app does: rooted at that directory.
SRC_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api" / "src"
sys.path.insert(0, str(SRC_ROOT))

from config import AppConfig  # noqa: E402
from models import Note, NoteChunk  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
app_config = AppConfig()


def run_migrations_offline() -> None:
    context.configure(
        url=app_config.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(app_config.DATABASE_URL)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
