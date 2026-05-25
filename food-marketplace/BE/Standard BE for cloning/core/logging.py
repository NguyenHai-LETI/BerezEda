import json
import logging
import os
from logging.handlers import RotatingFileHandler

from .config import ENVIRONMENT

LOG_DIR = os.path.join(os.path.dirname(__file__), "../../logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "wakeatte.log")


class CloudWatchJSONFormatter(logging.Formatter):
    """JSON formatter for CloudWatch logs in production"""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra data if present
        if hasattr(record, "error_data"):
            log_data["error_data"] = record.error_data

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# Configure logging format based on environment
if ENVIRONMENT.lower() == "production":
    # Use JSON format for CloudWatch in production
    formatter = CloudWatchJSONFormatter()
    log_format = formatter
else:
    # Use human-readable format for development/staging
    log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        if ENVIRONMENT.lower() != "production"
        else None
    ),
    handlers=[logging.StreamHandler()] if ENVIRONMENT.lower() == "production" else None,
)

logger = logging.getLogger("wakeatte")

# Configure handlers based on environment
if ENVIRONMENT.lower() == "production":
    # In production, use JSON format for CloudWatch
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CloudWatchJSONFormatter())
    logger.addHandler(console_handler)
else:
    # File handler for important logs (development/staging)
    # 10 files × 15MB = 150MB total log storage
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=15 * 1024 * 1024, backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    critical_file = os.path.join(LOG_DIR, "critical.log")
    critical_handler = RotatingFileHandler(
        critical_file, maxBytes=2 * 1024 * 1024, backupCount=2
    )
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(log_format)
    logger.addHandler(critical_handler)

    for myna_logger_name in ["apps.mynaportal", "apps.integrations.mynaportal"]:
        myna_logger = logging.getLogger(myna_logger_name)
        myna_logger.addHandler(file_handler)
