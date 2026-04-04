from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db import base  # noqa: F401  # Ensure all ORM models are imported and mapped

engine_kwargs = {"pool_pre_ping": True}

# Supabase transaction pooler (port 6543) is recommended for serverless runtimes
# such as Vercel. It doesn't work well with app-side connection pooling or
# prepared statements, so we disable both in that mode.
if settings.uses_supabase_transaction_pooler:
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {"prepare_threshold": None}

engine = create_engine(settings.sqlalchemy_database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
