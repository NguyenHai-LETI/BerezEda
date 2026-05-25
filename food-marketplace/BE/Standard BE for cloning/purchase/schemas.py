from typing import Optional

from pydantic import BaseModel, Field, model_validator

from apps.purchase.constants import *


class FincodeCustomerCreateRequest(BaseModel):
    id: str = Field(description="User ID")
    name: str
    email: str


class FincodeCardSessionRequest(BaseModel):
    customer_id: str = Field(description="User ID")
    customer_name: str = Field(description="User name")
    tds_type: str = Field(default=f"{TDS_TYPE_DEFAULT}")
    tds2_type: str = Field(default=f"{TDS2_TYPE_DEFAULT}")
    success_url: str = Field(description="Success callback URL")
    cancel_url: str = Field(description="Cancel callback URL")

    # @model_validator(mode="after")
    # def check_fields(self):
    #     if self.tds_type != TDS_TYPE_DEFAULT or self.tds2_type != TDS2_TYPE_DEFAULT:
    #         raise ValueError("3D Secure authentication is required for all transactions")


class UserCardInfo(BaseModel):
    card_id: str
    brand: str
    card_no: str
    expire: str
    holder_name: str
    is_default: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "brand": "VISA",
                "card_no": "************1111",
                "expire": "2512",
                "holder_name": "Nguyen Van A",
                "is_default": False,
            }
        }
    }


class PaymentChangeRequest(BaseModel):
    user_id: str
    shop_id: str
    order_number: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "53704ec6-c57a-43f5-8ce0-ee39b46ccbf0",
                "shop_id": "shop_123",
                "order_number": "order_20",
            }
        }
    }


class PaymentRequest(PaymentChangeRequest):
    amount: str
    card_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "53704ec6-c57a-43f5-8ce0-ee39b46ccbf0",
                "shop_id": "shop_123",
                "order_number": "order_20",
                "amount": "1000",
                "card_id": "cs_AmyuxPdCRX-Qg8T4wRPbCA",
            }
        }
    }


class PaymentCreateFincodeRequest(BaseModel):
    id: str = Field(description="Order ID")
    pay_type: str = Field(default=f"{PAY_TYPE_DEFAULT}")
    job_code: str = Field(default=f"{JOB_CODE_DEFAULT}")
    amount: str
    tds_type: str = Field(default=f"{TDS_TYPE_DEFAULT}")
    tds2_type: str = Field(default=f"{TDS2_TYPE_DEFAULT}")
    client_field_1: str = Field(description="Shop_id")

    @model_validator(mode="after")
    def check_fields(self):
        # TODO: bật 3D secure
        # if self.tds_type != TDS_TYPE_DEFAULT or self.tds2_type != TDS2_TYPE_DEFAULT:
        #     raise ValueError("3D Secure authentication is required for all transactions")
        if self.pay_type != PAY_TYPE_DEFAULT:
            raise ValueError("Pay type must be specified as Card")
        if self.job_code != JOB_CODE_DEFAULT:
            raise ValueError("Job code must be specified as AUTH")
        return self


class PaymentExecuteFincodeRequest(BaseModel):
    access_id: str
    customer_id: str = Field(description="User_id")
    pay_type: str = Field(default="Card")
    method: str = Field(default=f"{PAYMENT_METHOD_DEFAULT}")
    return_url: str = Field(
        default=PAYMENT_EXECUTION_SUCCESS_URL,
        description="URL to redirect when payment is successful",
    )
    return_url_on_failure: str = Field(
        default=PAYMENT_REGISTRATION_FAILURE_URL,
        description="URL to redirect when payment fails",
    )

    @model_validator(mode="after")
    def check_fields(self):
        if self.pay_type != PAY_TYPE_DEFAULT:
            raise ValueError("Pay type must be specified as Card")
        if self.method != PAYMENT_METHOD_DEFAULT:
            raise ValueError("Payment method must equal 1")
        return self


class PaymentCaptureFincodeRequest(BaseModel):
    pay_type: str = Field(default="Card")
    access_id: str

    @model_validator(mode="after")
    def check_fields(self):
        if self.pay_type != PAY_TYPE_DEFAULT:
            raise ValueError("Pay type must be specified as Card")
        return self


class PaymentChangeFincodeRequest(BaseModel):
    pay_type: str = Field(default="Card")
    access_id: str
    amount: str
    job_code: str = Field(default=f"{JOB_CODE_DEFAULT}")

    @model_validator(mode="after")
    def check_fields(self):
        if self.job_code != JOB_CODE_DEFAULT:
            raise ValueError("Job code must be specified as CAPTURE")
        return self


class PaymentCancelFincodeRequest(BaseModel):
    """Request body for Fincode payment cancel (full refund)."""

    pay_type: str = Field(default="Card")
    access_id: str

    @model_validator(mode="after")
    def check_fields(self):
        if self.pay_type != PAY_TYPE_DEFAULT:
            raise ValueError("Pay type must be specified as Card")
        return self
