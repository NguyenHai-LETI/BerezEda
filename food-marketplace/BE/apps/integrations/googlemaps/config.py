import os

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Google Maps API configuration
GOOGLE_MAPS_BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# Travel modes mapping
TRAVEL_MODES = {
    "driving": "driving",
    "walk": "walking",
    "motorbike": "driving",  # Use driving mode for motorbike as it follows road rules
}


def validate_google_maps_config():
    """Validate Google Maps configuration"""
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable is required")
    return True
