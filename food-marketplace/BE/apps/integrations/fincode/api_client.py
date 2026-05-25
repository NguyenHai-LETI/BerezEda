from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException

from apps.core.logging import logger
from apps.integrations.fincode.exceptions import fincode_error
from apps.purchase.schemas import (
    FincodeCardSessionRequest,
    FincodeCustomerCreateRequest,
    PaymentCancelFincodeRequest,
    PaymentChangeFincodeRequest,
    PaymentCreateFincodeRequest,
    PaymentExecuteFincodeRequest,
)

from .config import (
    FINCODE_API_BASE_URL,
    FINCODE_CARD_SESSIONS_ENDPOINT,
    FINCODE_CUSTOMERS_ENDPOINT,
    FINCODE_PAYMENT_REGISTRATION_ENDPOINT,
    FINCODE_PUBLIC_KEY,
    FINCODE_SECRET_KEY,
    get_auth_headers,
)


class FincodeApiClient:

    def __init__(
        self, secret_key: Optional[str] = None, public_key: Optional[str] = None
    ):
        self.secret_key = FINCODE_SECRET_KEY
        self.public_key = FINCODE_PUBLIC_KEY
        self.base_url = FINCODE_API_BASE_URL
        self.max_retries = 3

    def close(self):
        print("Cleanup PaymentService")

    def _parse_response(self, response: requests.Response):
        status_code = response.status_code
        response_data = response.json()
        logger.warning(
            f"Receive Fincode response: Status={status_code} {response_data}"
        )
        if status_code == 200:
            return response_data
        else:
            error_status = status_code
            error_code = response_data["errors"][0].get("error_code")
            error_message = response_data["errors"][0].get("error_message")
            raise fincode_error(str(error_status), error_code, error_message)

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = None,
    ):
        logger.warning(f"Request to Fincode:{url} with data: {data}")

        if retries is None:
            retries = self.max_retries

        headers = headers or {}
        if not headers.get("Authorization") and self.secret_key:
            headers.update(get_auth_headers(self.secret_key))

        for attempt in range(retries + 1):
            response = requests.request(
                method=method, url=url, headers=headers, json=data, params=params
            )
            try:
                parsed_response = self._parse_response(response)
            except fincode_error as e:
                raise HTTPException(
                    status_code=int(e.error_status),
                    detail=f"Fincode Error {e.error_code}: {e.error_message}",
                )

            return parsed_response

    def get_customer_by_id(self, customer_id: str):
        url = f"{FINCODE_CUSTOMERS_ENDPOINT}/{customer_id}"
        response = self._make_request(method="GET", url=url)
        return response

    def register_new_customer(self, user_fincode: FincodeCustomerCreateRequest):
        response = self._make_request(
            method="POST",
            url=FINCODE_CUSTOMERS_ENDPOINT,
            data=user_fincode.model_dump(),
        )
        return response

    def register_new_card(self, card_session_request: FincodeCardSessionRequest):

        response = self._make_request(
            method="POST",
            url=FINCODE_CARD_SESSIONS_ENDPOINT,
            data=card_session_request.model_dump(),
        )
        return response

    def delete_card(self, user_id: str, card_id: str):
        response = self._make_request(
            method="DELETE",
            url=f"{FINCODE_CUSTOMERS_ENDPOINT}/{user_id}/cards/{card_id}",
        )
        return response

    def get_customer_cards(self, customer_id: str):

        url = f"{FINCODE_CUSTOMERS_ENDPOINT}/{customer_id}/cards"
        response = self._make_request(method="GET", url=url)
        return response

    def set_default_card(self, customer_id: str, card_id: str):
        url = f"{FINCODE_CUSTOMERS_ENDPOINT}/{customer_id}/cards/{card_id}"
        data = {"default_flag": "1"}
        response = self._make_request(method="PUT", url=url, data=data)
        return response

    def payment_registration(
        self,
        payment_registration_request: PaymentCreateFincodeRequest,
    ):
        response = self._make_request(
            method="POST",
            url=FINCODE_PAYMENT_REGISTRATION_ENDPOINT,
            data=payment_registration_request.model_dump(),
        )
        return response

    def payment_execution(
        self, order_id: str, payment_execution_request: PaymentExecuteFincodeRequest
    ):
        response = self._make_request(
            method="PUT",
            url=f"{FINCODE_PAYMENT_REGISTRATION_ENDPOINT}/{order_id}",
            data=payment_execution_request.model_dump(),
        )
        return response

    def payment_change(
        self, order_id: str, payment_change_request: PaymentChangeFincodeRequest
    ):
        response = self._make_request(
            method="PUT",
            url=f"{FINCODE_PAYMENT_REGISTRATION_ENDPOINT}/{order_id}/change",
            data=payment_change_request.model_dump(),
        )
        return response

    def payment_cancel(
        self, order_id: str, cancel_request: PaymentCancelFincodeRequest
    ):
        """Cancel (full refund) a captured payment. order_id = payments.order_id (Fincode payment id)."""
        response = self._make_request(
            method="PUT",
            url=f"{FINCODE_PAYMENT_REGISTRATION_ENDPOINT}/{order_id}/cancel",
            data=cancel_request.model_dump(),
        )
        return response
