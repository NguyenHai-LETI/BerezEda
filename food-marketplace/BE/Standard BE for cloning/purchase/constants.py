"""
For Paid
Submit Order → Pending Payment → Fincode Processing → Confirmed/Failed
For Free
Submit Order → MyNa Portal Check → Immediate Confirmation (no charge)
"""

from apps.core.config import DOMAIN

# Payment Status Lifecycle:
# UNPROCESSED -> CAPTURED (when payment executed)
# UNPROCESSED -> FAILED (when payment process fail)


PAYMENT_EXECUTION_SUCCESS_URL = (
    f"{DOMAIN}/api/purchase-callbacks/webhook/payment-execute"
)
PAYMENT_REGISTRATION_FAILURE_URL = f"{DOMAIN}/api/purchase-callbacks/payment/failure"
FINCODE_WEBHOOK_SIGNATURE = "Thisismywebhooksignature"
CAPTURE_SUCCESS_INFORMATION = "Payment has been successfully captured"
PAYMENT_SUCCESS_INFORMATION = "Payment authorized successfully"

NUMBER_REGISTED_CARD_LIMIT = 5
# TDS_TYPE_DEFAULT = "2"
# TDS2_TYPE_DEFAULT = "2"
TDS_TYPE_DEFAULT = "2"
TDS2_TYPE_DEFAULT = "2"
PAY_TYPE_DEFAULT = "Card"
JOB_CODE_DEFAULT = "CAPTURE"
PAYMENT_METHOD_DEFAULT = "1"
USER_ALREADY_REGISTERED = "this user is registered already"
USER_NOT_FOUND_DB_OR_FINCODE = "User is not register in database or fincode system"
REFUND_PENALTY_PERCENTAGE = 0.3

WAITING_3D_SECURE_STATUS = "AUTHENTICATED"

EXECUTED_PAYMENT_NOT_FOUND = (
    "This payment is executed successfully, but was not saved in database"
)
INVALID_ORDER_INFORMATION = "Provided order information is invalid"
CARD_REGISTRATION_LIMIT_EXCEEDED = (
    "The number of registered cards has reached the limit"
)
INVALID_CARD_OWNER = "Card does not belong to the current user"


ERROR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
</head>
<body>
    <h1>Error Processing Card Registration</h1>
    <p>An error occurred: {error}</p>
</body>
</html>
"""
