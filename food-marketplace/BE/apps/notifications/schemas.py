from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, model_validator


class NotificationCreate(BaseModel):
    title: str
    body: str
    type: str
    notification_type: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    created_by_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "string",
                "body": "string",
                "type": "string",
                "notification_type": "USER_BUY_COMBO",
                "target_type": "string",
                "target_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "created_by_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            }
        }
    }


class NotificationRead(BaseModel):
    id: UUID
    title: str
    body: str
    type: str
    notification_type: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[UUID] = None
    created_at: datetime
    created_by_id: Optional[UUID] = None
    created_by_role: Optional[str] = None  # Role of user who created the notification
    is_read: Optional[bool] = None
    confirm_content: Optional[str] = None
    shop_id: Optional[str] = None  # Shop ID from related order
    order_id: Optional[str] = None  # Order ID if target_type is "order"
    pickup_code: Optional[str] = None  # Pickup code from related order
    store_name: Optional[str] = None  # Shop name
    phone_number: Optional[str] = None  # Shop phone number

    model_config = {"from_attributes": True}

    @classmethod
    def build(
        cls, noti, noti_user=None, shop_info=None, order_info=None, created_by_role=None
    ):
        data = noti.model_dump()
        if noti_user:
            data["is_read"] = noti_user.is_read
            data["confirm_content"] = noti_user.confirm_content
        if shop_info:
            data["store_name"] = shop_info.get("store_name")
            data["phone_number"] = shop_info.get("phone_number")
        if order_info:
            data["order_id"] = order_info.get("order_id")
            data["shop_id"] = order_info.get("shop_id")
            data["pickup_code"] = order_info.get("pickup_code")
        if created_by_role:
            data["created_by_role"] = created_by_role
        return cls.model_validate(data)


class NotificationUpdate(BaseModel):
    confirm_content: str

    model_config = {"json_schema_extra": {"example": {"confirm_content": "受取完了"}}}


class NotificationConfirmRequest(BaseModel):
    confirm_content: str

    model_config = {
        "json_schema_extra": {
            "example": {"confirm_content": "すべて食べ終わりました"}
        }
    }


class NotificationUserRead(BaseModel):
    """Schema for NotificationUser response"""

    id: str
    notification_id: str
    email: str  # User email
    name: Optional[str] = None  # User name

    model_config = {"from_attributes": True}


class PushNotificationRequest(BaseModel):
    """Schema for sending push notifications to multiple users

    Note:
    - If push_to_all is True, user_ids must be empty or not provided.
    - If push_to_all is False, user_ids must be provided and not empty.
    """

    user_ids: Optional[list[str]] = None
    title: str
    body: str
    push_to_all: bool = False
    from_represent: str = "info"

    @model_validator(mode="after")
    def validate_user_ids(self):
        """
        Validate user_ids based on push_to_all flag.

        Note: If filter parameters are provided in query params, user_ids can be None.
        This validation will be checked in the router endpoint.
        """
        if self.push_to_all:
            # If push_to_all is True, user_ids must be empty or None
            if self.user_ids:
                raise ValueError(
                    "Cannot specify user_ids when push_to_all is True. user_ids must be empty when push_to_all=True"
                )
        # Note: user_ids validation when push_to_all=False is handled in the router
        # to allow for filter-based user selection
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_ids": [
                    "6ce3ed31-3ff7-447f-8b6e-fb62c96f5721",
                    "7de4fe42-4gg8-558g-9c7f-gc73d07g6832",
                ],
                "title": "Important Announcement",
                "body": "This is an important notification for all users.",
                "push_to_all": False,
                "from_represent": "info",
            }
        }
    }


class PushNotificationResponse(BaseModel):
    """Response schema for push notification sending"""

    total_users: int
    successful: int
    failed: int
    failed_user_ids: list[str]
    from_represent: str
    title: str
    body: str
    sent_at: datetime
    notification_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_users": 10,
                "successful": 8,
                "failed": 2,
                "failed_user_ids": [
                    "6ce3ed31-3ff7-447f-8b6e-fb62c96f5721",
                    "7de4fe42-4gg8-558g-9c7f-gc73d07g6832",
                ],
                "from_represent": "info",
                "title": "Important Announcement",
                "body": "This is an important notification for all users.",
                "sent_at": "2024-01-01T12:00:00",
                "notification_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            }
        }
    }
