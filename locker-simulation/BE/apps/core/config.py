import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345678@localhost:5432/locker_simulation")
SYSTEM1_URL = os.getenv("SYSTEM1_URL", "http://localhost:8000/api")
API_PREFIX = "/api"
