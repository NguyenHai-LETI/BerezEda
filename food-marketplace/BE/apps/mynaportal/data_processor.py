"""Data processing utilities for MynaPortal welfare information."""

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from apps.integrations.mynaportal import DATE_FIELD_MAPPINGS, LOCATION_KEY

logger = logging.getLogger(__name__)


def parse_date_start(date_str: str) -> date:
    """
    Parse date string to date object (first day of month for YYYYMM).
    """
    if "-" in date_str:
        parts = date_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        return date(year, month, 1)


def parse_date_end(date_str: str) -> date:
    """
    Parse end date string to date object (last day of month for YYYYMM).
    """
    if "-" in date_str:
        parts = date_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        # Calculate last day of month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return next_month - timedelta(days=1)


def is_welfare_support_active(
    start_date_str: str, end_date_str: str, current_date: Optional[date] = None
) -> bool:
    """
    Check if a welfare support period is currently active.
    """
    if current_date is None:
        current_date = date.today()

    start = parse_date_start(start_date_str)
    end = parse_date_end(end_date_str)
    return start <= current_date <= end


class WelfareDataProcessor:
    """Processes and validates welfare information from MynaPortal."""

    @staticmethod
    def _find_welfare_info(location_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Find and extract welfare information from location data.

        Args:
            location_data: Dictionary containing welfare information for a location

        Returns:
            Dictionary with welfare info or None if not found
        """
        for welfare_type, field_mapping in DATE_FIELD_MAPPINGS.items():
            if welfare_type in location_data:
                try:
                    return WelfareDataProcessor._extract_dates_from_welfare_type(
                        location_data[welfare_type], welfare_type, field_mapping
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract dates from {welfare_type}: {e}")
                    continue

        return None

    @staticmethod
    def _extract_dates_from_welfare_type(
        welfare_data: Any, welfare_type: str, field_mapping: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Extract start and end dates from specific welfare type data.

        Args:
            welfare_data: The welfare data structure
            welfare_type: Type of welfare information
            field_mapping: Field mapping configuration

        Returns:
            Dictionary containing message, start_date, and end_date
        """
        start_field = field_mapping["start_field"]
        end_field = field_mapping["end_field"]
        nested_path = field_mapping.get("nested_path", [])

        # Navigate through nested structure if specified
        current_data = welfare_data
        for path_segment in nested_path:
            if isinstance(current_data, list) and current_data:
                current_data = current_data[0][path_segment]
            else:
                current_data = current_data[path_segment]

        # Extract dates
        if isinstance(current_data, list) and len(current_data) >= 2:
            start_date = current_data[0][start_field]
            end_date = current_data[1][end_field]
        else:
            # Fallback for different data structures
            start_date = current_data[0][start_field]
            end_date = current_data[1][end_field]

        return {"message": welfare_type, "start_date": start_date, "end_date": end_date}

    @staticmethod
    def extract_all_welfare_types(
        self_personal_data: Optional[str],
    ) -> List[Dict[str, str]]:
        """
        Extract all welfare types from personal data.

        Args:
            self_personal_data: JSON string containing personal welfare data

        Returns:
            List of dictionaries, each containing message, start_date, and end_date
        """
        if not self_personal_data:
            return []

        welfare_types: List[Dict[str, str]] = []

        try:
            input_data = json.loads(self_personal_data)
            if not input_data:
                return []

            for object_data in input_data:
                if LOCATION_KEY not in object_data:
                    continue

                location_data = object_data[LOCATION_KEY]

                # Extract all welfare types from this location
                for welfare_type, field_mapping in DATE_FIELD_MAPPINGS.items():
                    if welfare_type in location_data:
                        try:
                            welfare_info = (
                                WelfareDataProcessor._extract_dates_from_welfare_type(
                                    location_data[welfare_type],
                                    welfare_type,
                                    field_mapping,
                                )
                            )
                            welfare_types.append(welfare_info)
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract dates from {welfare_type}: {e}"
                            )
                            continue

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse welfare data JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing welfare data: {e}")

        return welfare_types
