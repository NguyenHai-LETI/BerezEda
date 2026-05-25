import logging
import httpx
from typing import Optional

from apps.core.config import FINCODE_API_BASE_URL, FINCODE_SECRET_KEY

logger = logging.getLogger(__name__)

FRONTEND_BASE_URL = "http://localhost:3000"
CARD_CANCEL_URL = f"{FRONTEND_BASE_URL}/payment/select"
PAYMENT_RETURN_URL = f"{FRONTEND_BASE_URL}/payment/select"
PAYMENT_RETURN_FAIL_URL = f"{FRONTEND_BASE_URL}/payment/select"


class FincodeClient:
    def __init__(self):
        self.base_url = FINCODE_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {FINCODE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=30) as client:
                resp = getattr(client, method)(url, headers=self.headers, **kwargs)
                if resp.status_code >= 400:
                    error_body = resp.text
                    logger.error(f"Fincode {method.upper()} {path} => {resp.status_code}: {error_body}")
                    # Parse Fincode error details
                    try:
                        error_json = resp.json()
                        errors = error_json.get("errors", [])
                        if errors:
                            error_detail = "; ".join(
                                f"{e.get('error_code', '')}: {e.get('error_message', '')}"
                                for e in errors
                            )
                        else:
                            error_detail = error_body
                    except Exception:
                        error_detail = error_body
                    raise Exception(f"Fincode {resp.status_code} {path}: {error_detail}")
                return resp.json()
        except Exception as e:
            logger.error(f"Fincode request error: {e}")
            raise

    # ── Customer ────────────────────────────────────────────────────────────────

    def create_customer(self, customer_id: str, email: str, name: str = "") -> dict:
        payload = {"id": customer_id, "email": email}
        if name:
            payload["name"] = name
        return self._request("post", "/v1/customers", json=payload)

    def get_customer(self, customer_id: str) -> Optional[dict]:
        try:
            return self._request("get", f"/v1/customers/{customer_id}")
        except Exception:
            return None

    # ── Card session (registration flow) ────────────────────────────────────────

    def create_card_session(self, customer_id: str, customer_name: str = "", combo_id: str = "") -> dict:
        """
        Create a card registration session.
        Returns { "link_url": "https://card.test.fincode.jp/sessions/..." }
        Frontend opens link_url in browser/webview so user can enter card info.
        After user submits, Fincode calls the card-registration webhook.
        """
        success_url = (
            f"{FRONTEND_BASE_URL}/payment/card-callback?combo_id={combo_id}"
            if combo_id
            else f"{FRONTEND_BASE_URL}/payment/card-callback"
        )
        return self._request(
            "post",
            "/v1/card_sessions",
            json={
                "customer_id": customer_id,
                "customer_name": customer_name,
                "tds_type": "0",
                "success_url": success_url,
                "cancel_url": CARD_CANCEL_URL,
            },
        )

    # ── Card management ─────────────────────────────────────────────────────────

    def list_cards(self, customer_id: str) -> list:
        try:
            data = self._request("get", f"/v1/customers/{customer_id}/cards")
            return data.get("list", [])
        except Exception:
            return []

    def set_default_card(self, customer_id: str, card_id: str) -> dict:
        return self._request(
            "put",
            f"/v1/customers/{customer_id}/cards/{card_id}",
            json={"default_flag": "1"},
        )

    def delete_card(self, customer_id: str, card_id: str) -> dict:
        return self._request("delete", f"/v1/customers/{customer_id}/cards/{card_id}")

    # ── Payment ─────────────────────────────────────────────────────────────────

    def register_payment(self, order_id: str, amount: int, shop_id: str = "") -> dict:
        """
        Step 1: Register a payment intent with Fincode.
        Returns { "id": order_id, "access_id": "a_...", "status": "UNPROCESSED", ... }
        """
        payload = {
            "id": order_id,
            "pay_type": "Card",
            "job_code": "CAPTURE",
            "amount": str(amount),
            "tds_type": "0",
        }
        if shop_id:
            payload["client_field_1"] = shop_id
        return self._request("post", "/v1/payments", json=payload)

    def execute_payment(self, order_id: str, access_id: str, customer_id: str, card_id: str = "") -> dict:
        """
        Step 2: Execute the registered payment using a specific card.
        access_id comes from register_payment response.
        Returns { "status": "CAPTURED" | "AUTHENTICATED", ... }
        """
        payload = {
            "pay_type": "Card",
            "access_id": access_id,
            "customer_id": customer_id,
            "method": "1",
            "return_url": PAYMENT_RETURN_URL,
            "return_url_on_failure": PAYMENT_RETURN_FAIL_URL,
        }
        if card_id:
            payload["card_id"] = card_id
        return self._request("put", f"/v1/payments/{order_id}", json=payload)

    def get_payment(self, payment_id: str) -> dict:
        return self._request("get", f"/v1/payments/{payment_id}")

    def change_payment(self, order_id: str, access_id: str, new_amount: int) -> dict:
        """Partial refund — used for cancel-with-penalty (30% kept)."""
        return self._request(
            "put",
            f"/v1/payments/{order_id}/change",
            json={
                "pay_type": "Card",
                "access_id": access_id,
                "amount": str(new_amount),
                "job_code": "CAPTURE",
            },
        )


fincode_client = FincodeClient()
