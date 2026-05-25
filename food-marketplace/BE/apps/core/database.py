from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from apps.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)


def _safe_add_columns():
    """
    Add new columns to existing tables that were added after initial migration.
    Uses IF NOT EXISTS / exception-safe patterns so it is idempotent.
    """
    migrations = [
        # card table — add holder_name
        "ALTER TABLE card ADD COLUMN IF NOT EXISTS holder_name VARCHAR(100) DEFAULT NULL",
        # payments table — add fincode_access_id and card_id
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS fincode_access_id VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS card_id VARCHAR(100) DEFAULT NULL",
        # combo table — add image
        "ALTER TABLE combo ADD COLUMN IF NOT EXISTS image VARCHAR(500) DEFAULT NULL",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()


def init_db():
    SQLModel.metadata.create_all(engine)
    _safe_add_columns()


def get_session():
    with Session(engine) as session:
        yield session


@contextmanager
def get_sync_session():
    with Session(engine) as session:
        yield session
