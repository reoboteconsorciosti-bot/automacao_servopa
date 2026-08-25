"""
Conexão centralizada com o banco de dados (equivalente ao prisma.ts no Next.js).

Toda a aplicação (rotas, models, serviços e Alembic) deve importar engine, Base,
SessionLocal e get_db exclusivamente deste arquivo. Nunca crie um novo engine ou
Base declarativa em outro lugar.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()



DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/servopa_automacao",
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. Defina esta variável no arquivo .env."
    )

# Normaliza o esquema antigo "postgres://" (comum em serviços de banco
# gerenciados, ex.: Heroku/Railway/EasyPanel) para "postgresql://". O
# SQLAlchemy 2.x removeu o dialeto "postgres" e quebra com
# NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres
# se a URL vier nesse formato antigo.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]


def _build_engine() -> Engine:
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


engine: Engine = _build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    class_=Session,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Gerencia o ciclo de vida de uma sessão (FastAPI dependency).

    Exemplo de uso em rotas:
        @router.get("/users")
        def list_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["DATABASE_URL", "engine", "SessionLocal", "Base", "get_db"]
