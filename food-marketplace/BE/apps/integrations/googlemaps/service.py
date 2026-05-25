import logging
from typing import Any, Dict, List, Optional

import aiohttp

from apps.integrations.googlemaps.config import (
    GOOGLE_MAPS_API_KEY,
    GOOGLE_MAPS_BASE_URL,
    TRAVEL_MODES,
    validate_google_maps_config,
)

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service for Google Maps Distance Matrix API integration"""

    def __init__(self):
        validate_google_maps_config()
        self.api_key = GOOGLE_MAPS_API_KEY
        self.base_url = GOOGLE_MAPS_BASE_URL

    async def calculate_distance(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        mode: str = "driving",
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate distance and duration between origin and destination

        Args:
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            destination_lat: Destination latitude
            destination_lng: Destination longitude
            mode: Travel mode (driving, walk, motorbike)

        Returns:
            Dict with distance and duration information or None if error
        """
        try:
            # Validate travel mode
            if mode not in TRAVEL_MODES:
                logger.warning(
                    f"Invalid travel mode: {mode}. Using 'driving' as default."
                )
                mode = "driving"

            travel_mode = TRAVEL_MODES[mode]

            # Build API parameters
            origin = f"{origin_lat},{origin_lng}"
            destination = f"{destination_lat},{destination_lng}"

            params = {
                "origins": origin,
                "destinations": destination,
                "mode": travel_mode,
                "units": "metric",
                "key": self.api_key,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_distance_response(data)
                    else:
                        logger.error(f"Google Maps API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return None

    async def calculate_multiple_distances(
        self,
        origin_lat: float,
        origin_lng: float,
        destinations: List[Dict[str, float]],
        mode: str = "driving",
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Calculate distances to multiple destinations

        Args:
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            destinations: List of dicts with 'lat' and 'lng' keys
            mode: Travel mode (driving, walk, motorbike)

        Returns:
            List of distance/duration dicts or None for errors
        """
        try:
            # Validate travel mode
            if mode not in TRAVEL_MODES:
                logger.warning(
                    f"Invalid travel mode: {mode}. Using 'driving' as default."
                )
                mode = "driving"

            travel_mode = TRAVEL_MODES[mode]

            # Build destinations string
            origin = f"{origin_lat},{origin_lng}"
            destinations_str = "|".join(
                [f"{dest['lat']},{dest['lng']}" for dest in destinations]
            )

            params = {
                "origins": origin,
                "destinations": destinations_str,
                "mode": travel_mode,
                "units": "metric",
                "key": self.api_key,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_multiple_distances_response(data)
                    else:
                        logger.error(f"Google Maps API error: {response.status}")
                        return [None] * len(destinations)

        except Exception as e:
            logger.error(f"Error calculating multiple distances: {str(e)}")
            return [None] * len(destinations)

    def _parse_distance_response(self, data: dict) -> Optional[Dict[str, Any]]:
        """Parse single distance response from Google Maps API"""
        try:
            if data.get("status") != "OK":
                logger.error(f"Google Maps API returned status: {data.get('status')}")
                return None

            rows = data.get("rows", [])
            if not rows:
                return None

            elements = rows[0].get("elements", [])
            if not elements:
                return None

            element = elements[0]
            if element.get("status") != "OK":
                logger.error(f"Distance calculation failed: {element.get('status')}")
                return None

            distance = element.get("distance", {})
            duration = element.get("duration", {})

            return {
                "distance": {
                    "text": distance.get("text", ""),
                    "value": distance.get("value", 0),  # meters
                },
                "duration": {
                    "text": duration.get("text", ""),
                    "value": duration.get("value", 0),  # seconds
                },
            }

        except Exception as e:
            logger.error(f"Error parsing distance response: {str(e)}")
            return None

    def _parse_multiple_distances_response(
        self, data: dict
    ) -> List[Optional[Dict[str, Any]]]:
        """Parse multiple distances response from Google Maps API"""
        try:
            if data.get("status") != "OK":
                logger.error(f"Google Maps API returned status: {data.get('status')}")
                return []

            rows = data.get("rows", [])
            if not rows:
                return []

            elements = rows[0].get("elements", [])
            results = []

            for element in elements:
                if element.get("status") == "OK":
                    distance = element.get("distance", {})
                    duration = element.get("duration", {})

                    results.append(
                        {
                            "distance": {
                                "text": distance.get("text", ""),
                                "value": distance.get("value", 0),
                            },
                            "duration": {
                                "text": duration.get("text", ""),
                                "value": duration.get("value", 0),
                            },
                        }
                    )
                else:
                    results.append(None)

            return results

        except Exception as e:
            logger.error(f"Error parsing multiple distances response: {str(e)}")
            return []


# Global instance
google_maps_service = GoogleMapsService()
