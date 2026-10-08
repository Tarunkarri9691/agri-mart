"""Alembic environment: uses the same DATABASE_URL and models as the app."""
from alembic import context
from sqlalchemy import engine_from_config, pool

from app import config, models  # noqa: F401  (registers tables)
from app.database import Base

cfg = context.config
cfg.set_main_option("sqlalchemy.url", config.DATABASE_URL)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=config.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = engine_from_config(cfg.get_section(cfg.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=conn.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
