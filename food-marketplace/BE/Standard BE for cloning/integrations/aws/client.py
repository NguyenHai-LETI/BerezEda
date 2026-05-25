import os
from typing import Any, Optional

import boto3

from apps.core.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from apps.core.logging import logger


def get_aws_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get AWS credentials from config."""
    return AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def create_aws_client(service_name: str, region_name: Optional[str] = None) -> Any:
    """
    Create an AWS service client with shared configuration.

    Args:
        service_name: AWS service name (e.g., 's3', 'ses')
        region_name: AWS region (optional, defaults based on service)

    Returns:
        boto3.client: Configured AWS client

    Raises:
        ValueError: If credentials are missing
    """
    access_key, secret_key = get_aws_credentials()

    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in configuration")

    # Default regions for different services
    default_regions = {
        "s3": "ap-northeast-1",
        "ses": "ap-northeast-1",
    }

    if region_name is None:
        region_name = os.getenv(
            f"AWS_{service_name.upper()}_REGION",
            default_regions.get(service_name, "us-east-1"),
        )

    try:
        client = boto3.client(
            service_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

        logger.debug(f"Created AWS {service_name} client for region {region_name}")
        return client

    except Exception as e:
        logger.error(f"Failed to create AWS {service_name} client: {str(e)}")
        raise


def get_s3_client() -> Any:
    """Get configured S3 client."""
    return create_aws_client("s3")


def get_ses_client() -> Any:
    """Get configured SES client."""
    return create_aws_client("ses")
