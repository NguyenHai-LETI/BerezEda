"""Service layer for MynaPortal operations."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union

from sqlmodel import Session

from apps.integrations.mynaportal import (
    MAX_POLLING_ATTEMPTS,
    POLLING_INTERVAL_SECONDS,
    STATUS_VALUES,
    MynaAuthorizerNotFoundException,
    MynaPortalApiClient,
    MynaRequestException,
    MynaResultException,
    MynaTokenException,
)

from .crud import (
    create_user_welfare_supports,
    get_myna_authorizer_by_state,
    get_myna_authorizer_by_state_and_status,
    update_myna_authorizer,
    update_myna_authorizer_status,
)
from .data_processor import WelfareDataProcessor
from .logger import MynaLogger

logger = logging.getLogger(__name__)


class MynaPortalService:
    """Service for orchestrating MynaPortal operations."""

    def __init__(self, code: str, state: str, db: Session):
        """
        Initialize the service.

        Args:
            code: Authorization code
            state: State parameter
            db: Database session
        """
        self.api_client = MynaPortalApiClient(code, state)
        self.logger = MynaLogger()
        self.data_processor = WelfareDataProcessor()
        self.state = state
        self.db = db
        self._process_id = None  # Will be set after data request submission

    def get_myna_authorizer(self):
        """
        Get MynaAuthorizer instance by state.

        Returns:
            MynaAuthorizer instance

        Raises:
            MynaAuthorizerNotFoundException: If authorizer not found
        """
        myna_authorizer = get_myna_authorizer_by_state(self.db, self.state)
        if not myna_authorizer:
            raise MynaAuthorizerNotFoundException(
                f"MynaAuthorizer not found for state: {self.state}"
            )
        return myna_authorizer

    async def execute_full_workflow(self, user) -> Union[Dict[str, str], bool, None]:
        """
        Execute the complete MynaPortal workflow.

        Args:
            user: User instance

        Returns:
            Welfare information dictionary, False on error, or None
        """
        myna_object = self.get_myna_authorizer()
        myna_object.user_id = user.id
        myna_object.status = STATUS_VALUES["WAIT_RESULT"]

        try:
            token_response = self._get_access_token(myna_object)
            if not token_response:
                return False

            request_success = self._submit_data_request(myna_object, token_response)
            if not request_success:
                return False

            return await self._poll_for_results(myna_object)

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            myna_object.status = STATUS_VALUES["ERROR"]
            myna_object.error_description = str(e)
            self._save_myna_object(myna_object)
            return False

    def _get_access_token(self, myna_object) -> Optional[Dict[str, Any]]:
        """
        Get access token and update myna_object.

        Args:
            myna_object: MynaAuthorizer instance

        Returns:
            Token response or None on failure
        """
        try:
            token_response = self.api_client.get_access_token()

            if not isinstance(token_response, dict):
                myna_object.error_response = token_response
                raise MynaTokenException("Invalid token response format")

            myna_object.oauth_token_response = token_response
            myna_object.access_token = token_response["access_token"]

            logger.info("Successfully obtained access token")
            return token_response

        except MynaTokenException as e:
            logger.error(f"Token acquisition failed: {e}")
            myna_object.error_description = str(e)
            return None

    def _submit_data_request(self, myna_object, token_response: Dict[str, Any]) -> bool:
        """
        Submit data provision request.

        Args:
            myna_object: MynaAuthorizer instance
            token_response: Token response from previous step

        Returns:
            True on success, False on failure
        """
        try:
            access_token = token_response["access_token"]
            date = self.api_client.get_inquiry_date()
            telegram_id = self.api_client.generate_telegram_id(date)

            request_response = self.api_client.submit_data_request(
                access_token, telegram_id, date
            )

            if not isinstance(request_response, dict):
                myna_object.error_response = request_response
                raise MynaRequestException("Invalid request response format")

            myna_object.request_response = request_response

            common_header = request_response["commonHeader"]
            process_id = common_header["processId"]

            myna_object.telegramId = telegram_id
            myna_object.processId = process_id

            # Store processId for polling to query by processId
            self._process_id = process_id

            logger.info(f"Successfully submitted data request: {process_id}")
            return True

        except MynaRequestException as e:
            logger.error(f"Data request submission failed: {e}")
            myna_object.error_description = str(e)
            return False

    async def _poll_for_results(self, myna_object) -> Union[Dict[str, str], None]:
        """
        Poll for result availability and process data.

        Args:
            myna_object: MynaAuthorizer instance

        Returns:
            Processed welfare data or None
        """
        self._save_myna_object(myna_object)

        for attempt in range(MAX_POLLING_ATTEMPTS):
            await asyncio.sleep(POLLING_INTERVAL_SECONDS)  # ✅ Non-blocking sleep

            # Re-fetch the object to check if status changed
            updated_myna_object = self._get_updated_myna_object()

            if (
                updated_myna_object
                and updated_myna_object.status == STATUS_VALUES["REGISTER"]
            ):
                logger.info(
                    f"Status changed to REGISTER detected at attempt {attempt + 1}/{MAX_POLLING_ATTEMPTS}"
                )
                return self._process_final_result(updated_myna_object)

            # Log current status for debugging
            current_obj = get_myna_authorizer_by_state(self.db, self.state)
            current_status = current_obj.status if current_obj else "NOT_FOUND"
            logger.info(
                f"Polling attempt {attempt + 1}/{MAX_POLLING_ATTEMPTS} - "
                f"Current status: {current_status}, "
                f"Looking for: REGISTER, "
                f"ProcessId: {getattr(self, '_process_id', 'N/A')}"
            )

        logger.warning("Polling timeout reached")
        if self._process_id:
            update_myna_authorizer_status(self.db, self._process_id, STATUS_VALUES["TIMEOUT"])
        return None

    def _get_updated_myna_object(self):
        """
        Get updated MynaAuthorizer object from database.

        Returns:
            Updated MynaAuthorizer instance or None
        """
        # Expire all objects in session to force fresh query from database
        # This ensures we see the latest status updated by callback endpoint
        self.db.expire_all()

        # Try querying by processId first (callback updates by processId)
        if hasattr(self, "_process_id") and self._process_id:
            from apps.mynaportal.crud import get_myna_authorizer_by_process_id

            obj = get_myna_authorizer_by_process_id(self.db, self._process_id)
            if obj and obj.status == STATUS_VALUES["REGISTER"]:
                logger.info(
                    f"Found updated object by processId: {self._process_id}, status: {obj.status}"
                )
                return obj

        # Fallback to query by state and status
        obj = get_myna_authorizer_by_state_and_status(
            self.db, self.state, STATUS_VALUES["REGISTER"]
        )
        if obj:
            logger.info(
                f"Found updated object by state: {self.state}, status: {obj.status}"
            )
        return obj

    def _process_final_result(self, myna_object) -> Optional[Dict[str, str]]:
        """
        Process the final result and extract welfare information.

        Args:
            myna_object: MynaAuthorizer instance with registered status

        Returns:
            Processed welfare information
        """
        try:
            request_response = myna_object.request_response
            common_header = request_response["commonHeader"]
            mode = common_header["mode"]

            result_response = self.api_client.get_result(
                myna_object.access_token,
                myna_object.telegramId,
                myna_object.processId,
                mode,
            )

            self.logger.log_result_to_csv(result_response, myna_object)

            if not isinstance(result_response, dict):
                myna_object.error_response = result_response
                raise MynaResultException("Invalid result response format")

            # Parse selfPersonalData if it's a JSON string to preserve Japanese characters
            # PostgreSQL JSONB type supports UTF-8 natively, but we need to parse
            # the inner JSON string to convert Unicode escape sequences to UTF-8
            if "selfPersonalDataProvisionInfo" in result_response:
                self_personal_data_info = result_response[
                    "selfPersonalDataProvisionInfo"
                ]
                if "selfPersonalData" in self_personal_data_info:
                    self_personal_data = self_personal_data_info["selfPersonalData"]
                    # If selfPersonalData is a string (JSON with escape sequences), parse it
                    if isinstance(self_personal_data, str):
                        try:
                            self_personal_data_info["selfPersonalData"] = json.loads(
                                self_personal_data
                            )
                            logger.info(
                                "Parsed selfPersonalData JSON string to preserve Japanese characters"
                            )
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"Failed to parse selfPersonalData JSON string: {e}. "
                                "Keeping as string."
                            )

            # Save the processed result_response with parsed selfPersonalData
            myna_object.result_response = result_response

            # Process the welfare data and save to database
            # Get user_id from myna_object
            user_id = getattr(myna_object, "user_id", None)
            result_data = self.process_result_data(myna_object, user_id)

            logger.info("Successfully processed final result")

            # Return welfare_info for backward compatibility
            if result_data:
                return result_data.get("welfare_info")
            return None

        except Exception as e:
            logger.error(f"Final result processing failed: {e}")
            myna_object.status = STATUS_VALUES["ERROR"]
            myna_object.error_description = str(e)
            return None
        finally:
            self._save_myna_object(myna_object)

    def process_result_data(
        self, myna_object, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process and extract welfare information from result data.
        Also saves welfare supports to database and returns all welfare types.

        Args:
            myna_object: MynaAuthorizer instance with result data
            user_id: Optional user ID to save welfare supports for

        Returns:
            Dictionary with welfare_info and all_welfare_types, or None
        """
        try:
            result_response = getattr(myna_object, "result_response", {})
            self_personal_data = result_response.get(
                "selfPersonalDataProvisionInfo", {}
            ).get("selfPersonalData")

            # Ensure selfPersonalData is a string for extract methods
            if self_personal_data is not None and not isinstance(
                self_personal_data, str
            ):
                self_personal_data = json.dumps(self_personal_data, ensure_ascii=False)

            # Extract all welfare types
            all_welfare_types = self.data_processor.extract_all_welfare_types(
                self_personal_data
            )

            # Save welfare supports to database if user_id is provided
            if user_id and all_welfare_types:
                create_user_welfare_supports(
                    self.db,
                    user_id,
                    all_welfare_types,
                    myna_object.id,
                )
                logger.info(
                    f"Saved {len(all_welfare_types)} welfare supports for user {user_id}"
                )

            # Use first welfare type for backward compatibility (avoid redundant parsing)
            welfare_info = all_welfare_types[0] if all_welfare_types else None

            return {
                "welfare_info": welfare_info,
                "all_welfare_types": all_welfare_types,
            }

        except Exception as e:
            logger.error(f"Error processing result data: {e}")
            myna_object.status = STATUS_VALUES["ERROR"]
            myna_object.error_description = str(e)
            return None

    def _save_myna_object(self, myna_object):
        """
        Save MynaAuthorizer object with current timestamp.

        Args:
            myna_object: MynaAuthorizer instance to save
        """
        try:
            update_myna_authorizer(self.db, myna_object)
        except Exception as e:
            logger.error(f"Failed to save myna_object: {e}")
