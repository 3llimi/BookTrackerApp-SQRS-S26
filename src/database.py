import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()  # so a local .env is read before DATABASE_URL is looked up

# Local dev: SQLite = just a file called books.db, no server needed.
# Production: set DATABASE_URL to a Postgres connection string (e.g. Neon).
DEFAULT_DATABASE_URL = "sqlite:///./books.db"


def _normalize_database_url(url: str) -> str:
    """Make hosted-provider URLs work with SQLAlchemy + psycopg (v3)."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_database_url(
    os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
)

if DATABASE_URL.startswith("sqlite"):
    # check_same_thread is needed for SQLite only
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping: recover from connections that a serverless DB (Neon)
    # closed while the API was idle.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ── Dependency used in every router ──────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db  # gives the session to the route
    finally:
        db.close()  # always closes after the request is done
