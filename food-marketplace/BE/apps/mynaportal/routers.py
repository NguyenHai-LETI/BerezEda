import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from apps.auth.permissions import AuthenticatedUser
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.mynaportal.crud import get_myna_authorizer_by_process_id, update_myna_authorizer_status
from apps.mynaportal.schemas import (
    MynaAuthorizerCreateRequest,
    MynaAuthorizerResponse,
    MynaCallbackRequest,
)
from apps.mynaportal.services import generate_authorize_link

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MynaPortal"])


@router.post("/users/myna_go_jp", response_model=dict)
def if00105_endpoint(
    request_response: MynaCallbackRequest, db: Session = Depends(get_session)
):
    """Handle callback from MynaPortal when processing is complete."""
    common_header = request_response.commonHeader
    logger.info(f"Data callback from MynaPortal: {request_response}")

    telegram_id = common_header.get("telegramId", "")
    telegram_type = "IFA0302-S01"
    mode = common_header.get("mode", "")
    process_id = common_header.get("processId", "")
    error_code = common_header.get("errorCode", "")

    logger.info(
        f"Received callback from MynaPortal - processId: {process_id}, "
        f"telegramId: {telegram_id}, mode: {mode}, errorCode: {error_code}"
    )

    response_data = {
        "commonHeader": {
            "telegramId": telegram_id,
            "telegramType": telegram_type,
            "mode": mode,
            "processId": process_id,
            "errorCode": error_code,
        }
    }

    # Only update to REGISTER if status is WAIT_RESULT (reject late callbacks)
    existing = get_myna_authorizer_by_process_id(db, process_id)
    if not existing:
        logger.warning(
            f"MynaAuthorizer not found for processId: {process_id} - "
            f"status update failed"
        )
    elif existing.status != "WAIT_RESULT":
        logger.warning(
            f"Late callback rejected for processId: {process_id} - "
            f"current status: {existing.status} (expected WAIT_RESULT)"
        )
    else:
        updated_obj = update_myna_authorizer_status(db, process_id, "REGISTER")
        if updated_obj:
            logger.info(
                f"Successfully updated MynaAuthorizer status to REGISTER - "
                f"processId: {process_id}, state: {updated_obj.state}, "
                f"user_id: {updated_obj.user_id}"
            )

    return response_data


@router.post("/users/mynumber", response_model=SuccessResponse[MynaAuthorizerResponse])
def create_myna_authorizer_endpoint(
    request: MynaAuthorizerCreateRequest,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Create a MynaAuthorizer and generate authorization link.

    This endpoint:
    1. Generates a unique state value
    2. Creates a MynaAuthorizer record in the database
    3. Generates and returns the MynaPortal authorization link
    """
    try:
        link_authorize = generate_authorize_link(db, user.id)
        response_data = MynaAuthorizerResponse(link_authorize=link_authorize)
        return SuccessResponse(data=response_data)

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to generate authorization link: {str(e)}"
        )
