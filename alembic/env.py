from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os, sys
from dotenv import load_dotenv

# let Alembic can import project app/ (let project root directory be added in PYTHONPATH)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from app.core.config import DATABASE_URL           
from app.db.session import Base                    # Base for autogenerate
from app.models.health_check import HealthCheck    # make sure models are loaded

config = context.config

# logging settings(can see Alembic execution log in CLI)
if config.config_file_name:
    # fileConfig(config.config_file_name)
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set the project's DB URL to Alembic to connect to the db
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Let autogenerate see all Table definitions, Base.metadata includes all ORMs that inherit Base
target_metadata = Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Do not actually connect to the db, only generates .sql
def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# create a database connection Engine
def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
