from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_URL = "sqlite:///./sre_agent.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, _):
     dbapi_connection.execute("PRAGMA journal_mode=WAL")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
class Base(DeclarativeBase):
    pass