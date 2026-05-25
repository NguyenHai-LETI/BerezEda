import requests

from apps.core.config import ANDROID_PACKAGE_NAME, BRANCHIO_KEY, DOMAIN


def create_branchio_deeplink(data: dict) -> str:
    """
    Create a Branch.io deep link using the Branch API.
    """
    url = f"https://api2.branch.io/v1/url"
    payload = {"branch_key": BRANCHIO_KEY, **data}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json().get("url")


def create_deeplink_data(
    original_path: str, name_feature: str, data: dict = None
) -> dict:
    deeplink_data = {
        "data": {
            "$ios_bundle_id": "info.wake.wakeatte",
            "$android_package_name": ANDROID_PACKAGE_NAME,
            "$fallback_url": f"{DOMAIN}/{original_path}",
            "$ios_app_store_id": "6752841773",
            "$canonical_url": f"{DOMAIN}/{original_path}",
            "original_path": original_path,
        },
        "feature": name_feature,
        "channel": "app",
    }
    if data:
        deeplink_data["data"].update(data)
    return deeplink_data
