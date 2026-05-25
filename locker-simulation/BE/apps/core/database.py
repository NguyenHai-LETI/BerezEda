from sqlmodel import SQLModel, create_engine, Session

from apps.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    # Models must be imported before create_all so SQLModel registers their tables
    from apps.locker_codes.models import LockerCode  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
