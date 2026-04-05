from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite = just a local file called books.db, no server needed
DATABASE_URL = "sqlite:///./books.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}  # needed for SQLite only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ── Dependency used in every router ──────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db  # gives the session to the route
    finally:
        db.close()  # always closes after the request is done
