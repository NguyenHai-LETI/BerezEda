import os

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set! Check AWS Secrets Manager configuration."
    )

print(
    f"🔗 Connecting to database: {DATABASE_URL[:50]}..."
)  # Show first 50 chars for debugging
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("true", "1", "yes")

# Configure connection pool settings for t3.micro RDS instance (max ~87 connections)
# With multiple ECS tasks, we need to be conservative with connection pools
engine = create_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    pool_size=5,  # Reduced: Number of connections to maintain in pool
    max_overflow=10,  # Reduced: Additional connections beyond pool_size
    pool_timeout=30,  # Reduced timeout for faster failure detection
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Validate connections before use
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def get_session():
    with SessionLocal() as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(bind=engine)
