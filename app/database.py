from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()

kwargs = {}
if settings.database_url.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}
    # in-memory sqlite needs one shared connection, otherwise every thread gets an empty db
    if settings.database_url in ("sqlite://", "sqlite:///:memory:"):
        kwargs["poolclass"] = StaticPool
else:
    kwargs["pool_pre_ping"] = True

engine = create_engine(settings.database_url, **kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
