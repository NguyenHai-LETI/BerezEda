import logging

import requests
from fastapi import APIRouter, Query

from apps.core.logging import logger
from apps.core.schemas import ErrorResponse, SuccessResponse

logger = logging.getLogger("wakeatte")

MLIT_URL = "https://www.mlit-data.jp/api/v1/"
MLIT_API_KEY = "TOJ~.jEAF6RMuMAAS_y5DoEnaSsu.iWF"

router = APIRouter(tags=["External"])


def get_prefecture_data():
    """
    Fetch prefecture data from the MLIT Data API.
    """
    headers = {"Content-Type": "application/json", "apikey": MLIT_API_KEY}
    payload = {"query": "{ prefecture {\n code\n name\n }\n}", "variables": {}}

    try:
        response = requests.post(MLIT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log the error or handle it as needed
        logger.error(f"Error fetching prefecture data: {e}")
        return None


def get_municipalities_data(pref_codes=None):
    """
    Fetch municipalities data from the MLIT Data API.
    """
    headers = {"Content-Type": "application/json", "apikey": MLIT_API_KEY}
    if pref_codes:
        payload = {
            "query": '{ municipalities(prefCodes:["%s"]) {\n    code\n    prefecture_code\n    name\n  }\n}'
            % pref_codes,
            "variables": {},
        }
    else:
        payload = {
            "query": "{ municipalities {\n    code\n    prefecture_code\n    name\n  }\n}",
            "variables": {},
        }

    try:
        response = requests.post(MLIT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log the error or handle it as needed
        logger.error(f"Error fetching municipalities data: {e}")
        return None


@router.get("/prefectures", response_model=SuccessResponse)
def prefectures():
    """
    Fetch and return prefecture data.
    """
    prefecture_data = get_prefecture_data()
    if prefecture_data is None:
        return ErrorResponse(message="エラーが発生しました。")
    return SuccessResponse(data=prefecture_data["data"])


@router.get("/municipalities", response_model=SuccessResponse)
def municipalities(code: str = Query(None, description="Prefecture code")):
    """
    Fetch and return municipalities data based on provided pref_codes.
    """
    municipalities_data = get_municipalities_data(code)
    if municipalities_data is None:
        return ErrorResponse(message="エラーが発生しました。")
    return SuccessResponse(data=municipalities_data["data"])
