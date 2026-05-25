"""Logging utilities for MynaPortal operations."""

import csv
import logging
import os
from typing import Any, Dict

from apps.integrations.mynaportal import CSV_LOG_FILE

logger = logging.getLogger(__name__)


class MynaLogger:
    """Handles logging for MynaPortal operations."""

    @staticmethod
    def log_result_to_csv(result_response: Dict[str, Any], myna_object: Any) -> None:
        """
        Log API result to CSV file.

        Args:
            result_response: The API response data
            myna_object: MynaAuthorizer instance
        """
        try:
            data_to_log = {
                "access_token": getattr(myna_object, "access_token", "N/A"),
                "telegramId": getattr(myna_object, "telegramId", "N/A"),
                "processId": getattr(myna_object, "processId", "N/A"),
                "mode": result_response.get("mode", "N/A"),
                "result_data": str(result_response),
                "status": getattr(myna_object, "status", "N/A"),
                "error_description": getattr(myna_object, "error_description", "N/A"),
            }

            file_exists = os.path.isfile(CSV_LOG_FILE)

            with open(CSV_LOG_FILE, mode="a", newline="", encoding="utf-8") as csvfile:
                fieldnames = data_to_log.keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow(data_to_log)

            logger.info(f"Logged result to CSV: {CSV_LOG_FILE}")

        except Exception as e:
            logger.error(f"Failed to log result to CSV: {e}")

    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Set up a logger with consistent formatting.

        Args:
            name: Logger name
            level: Logging level

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
