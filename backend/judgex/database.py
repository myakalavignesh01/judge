from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.schema import CreateColumn
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def upgrade_legacy_schema() -> None:
    """Add newly introduced nullable/defaulted columns to existing local databases."""
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            present = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                definition = str(CreateColumn(column).compile(dialect=engine.dialect))
                connection.exec_driver_sql(f"ALTER TABLE {preparer.quote(table.name)} ADD COLUMN {definition}")
        if inspector.has_table("users"):
            connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_provider_subject ON users (auth_provider, auth_subject)")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
