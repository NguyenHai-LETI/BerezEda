import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Get the project root directory (where .env should be)
    project_root = Path(__file__).parent.parent.parent
    dotenv_path = project_root / ".env"

    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"Loaded .env from: {dotenv_path}")
    else:
        print(f".env file not found at: {dotenv_path}")
except ImportError:
    print("python-dotenv not installed, using system environment variables only")

# --- ENVIRONMENT CONFIG ---
ENVIRONMENT = os.getenv(
    "ENVIRONMENT", "development"
)  # development, staging, production

# --- GOOGLE CHAT CONFIG ---
GOOGLE_CHAT_WEBHOOK_URL = os.getenv(
    "GOOGLE_CHAT_WEBHOOK_URL",
    "https://chat.googleapis.com/v1/spaces/AAQA3IGAKb4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=mkz2QHYdHDmea74JwnfV0yuOAIMORawmC33Tvrljerc",
)

# --- DATABASE CONFIG ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wakeatte:wakeatte@localhost:5432/wakeatte"
)

# --- GOOGLE_API_KEY ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- AWS S3 CONFIG ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_HOST_DOMAIN = os.getenv("AWS_HOST_DOMAIN")

# --- BRANCH.IO CONFIG ---
BRANCHIO_KEY = os.getenv("BRANCHIO_KEY", "key_live_mAFnLZBmPqhmbZXbSjJm1lnfuDaOrv9a")
BRANCHIO_SECRET = os.getenv(
    "BRANCHIO_SECRET", "secret_live_zEYwsIkr6oo6hzWDKRT0vwi5yAXVeY6j"
)

# --- REDIS CONFIG ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- PASSWORD RESET CONFIG ---
# TODO: re-set limitations spam
SESSION_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_TOKEN_EXPIRE_MINUTES", "10"))
RESET_CODE_EXPIRE_MINUTES = int(os.getenv("SESSION_TOKEN_EXPIRE_MINUTES", "5"))
FORGOT_PASSWORD_EMAIL_LIMIT = int(os.getenv("FORGOT_PASSWORD_EMAIL_LIMIT", "5"))
FORGOT_PASSWORD_EMAIL_WINDOW = int(os.getenv("FORGOT_PASSWORD_EMAIL_WINDOW", "3600"))
RESET_PASSWORD_LIMIT = int(os.getenv("NEW_RESET_PASSWORD_LIMIT", "5"))
RESET_PASSWORD_WINDOW = int(os.getenv("NEW_RESET_PASSWORD_WINDOW", "600"))


# Default avatar images
IMAGE_USER_MALE = (
    f"{AWS_HOST_DOMAIN}/avatar_default/male.jpg"
    if AWS_HOST_DOMAIN
    else "/default/male.jpg"
)

# Different constants between staging and honban
API_PREFIX = os.getenv("API_PREFIX", "/v1")  # For STAG: /api
DOMAIN = os.getenv(
    "DOMAIN", "https://staging-wake.wakeatte.net"
)  # For PROD: https://api.wakeatte.net
ANDROID_PACKAGE_NAME = os.getenv(
    "ANDROID_PACKAGE_NAME", "info.wake.wakeatte.staging"
)  # For PROD: info.wake.wakeatte

# Timing Constants (configurable via environment variables)
# Per spec: 1440-minutes preparation deadline
MIN_FREE_PURCHASE_INTERVAL = int(os.getenv("MIN_FREE_PURCHASE_INTERVAL", "1440"))

# Per spec: 20-minutes preparation deadline
COMBO_PREPARATION_TIME_MINUTES = int(os.getenv("COMBO_PREPARATION_TIME_MINUTES", "20"))

# Shop cooldown period in minutes
SHOP_COOLDOWN_MINUTES = int(os.getenv("SHOP_COOLDOWN_MINUTES", "5"))

# Per spec: 30-minute pickup deadline
PICK_UP_DEADLINE = int(os.getenv("PICK_UP_DEADLINE", "30"))
