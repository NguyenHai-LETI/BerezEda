import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except ImportError:
    pass

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345678@localhost:5432/berezh_eda")
API_PREFIX = os.getenv("API_PREFIX", "/api")
DOMAIN = os.getenv("DOMAIN", "http://localhost:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
IMAGE_USER_MALE = os.getenv("IMAGE_USER_MALE", "https://ui-avatars.com/api/?name=User&background=random")

# File storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "5"))

# SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "БережЕда <noreply@berezh-eda.ru>")

# Firebase
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "food-marketplace-192f7")
FIRESTORE_DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "")

# Fincode
FINCODE_API_BASE_URL = os.getenv("FINCODE_API_BASE_URL", "https://api.test.fincode.jp")
FINCODE_PUBLIC_KEY = os.getenv("FINCODE_PUBLIC_KEY", "")
FINCODE_SECRET_KEY = os.getenv("FINCODE_SECRET_KEY", "")
FINCODE_WEBHOOK_SECRET = os.getenv("FINCODE_WEBHOOK_SECRET", "")

# App timing
COMBO_PICKUP_DEADLINE_MINUTES = int(os.getenv("COMBO_PICKUP_DEADLINE_MINUTES", "30"))
COMBO_READY_TIMEOUT_MINUTES = int(os.getenv("COMBO_READY_TIMEOUT_MINUTES", "30"))
SHOP_COOLDOWN_MINUTES = int(os.getenv("SHOP_COOLDOWN_MINUTES", "5"))

# Locker Simulation System 2
LOCKER_SIM_URL = os.getenv("LOCKER_SIM_URL", "http://localhost:8001/api")
