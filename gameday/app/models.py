import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, ForeignKey, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

import os
# e.g. postgresql+psycopg://postgres:YOURPASSWORD@localhost:5432/gameday  (falls back to SQLite if unset)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///gameday.db")
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}),
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:8]

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: new_id("u"))
    name: Mapped[str]
    username: Mapped[str] = mapped_column(String, unique=True, index=True)  # stored lowercase
    email: Mapped[str] = mapped_column(String, unique=True, index=True)     # stored lowercase
    phone: Mapped[str]
    pw_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="guest")                      # guest | host
    address: Mapped[str | None] = mapped_column(default=None)

def init_db():
    Base.metadata.create_all(bind=engine)



