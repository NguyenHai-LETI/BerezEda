from typing import BinaryIO, Optional

from apps.core.config import AWS_STORAGE_BUCKET_NAME
from apps.core.logging import logger
from apps.integrations.aws.client import get_s3_client


def upload_file_to_s3(
    file: BinaryIO, filename: str, bucket_name: Optional[str] = None
) -> str:
    """
    Upload a file to an S3 bucket and return the file URL.

    Args:
        file: File object to upload
        filename: Name to give the file in S3
        bucket_name: S3 bucket name (optional, uses default from config)

    Returns:
        str: Public URL of the uploaded file

    Raises:
        Exception: If upload fails
    """
    if bucket_name is None:
        bucket_name = AWS_STORAGE_BUCKET_NAME

    if not bucket_name:
        raise ValueError("No S3 bucket name specified")

    s3_client = get_s3_client()

    try:
        s3_client.upload_fileobj(file, bucket_name, filename)
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"

        logger.info(f"File uploaded successfully to S3: {filename}")
        return file_url

    except Exception as e:
        logger.error(f"Error uploading file {filename} to S3: {str(e)}")
        raise


def delete_file_from_s3(filename: str, bucket_name: Optional[str] = None) -> bool:
    """
    Delete a file from an S3 bucket.

    Args:
        filename: Name of the file to delete
        bucket_name: S3 bucket name (optional, uses default from config)

    Returns:
        bool: True if deletion successful, False otherwise
    """
    if bucket_name is None:
        bucket_name = AWS_STORAGE_BUCKET_NAME

    if not bucket_name:
        logger.error("No S3 bucket name specified")
        return False

    s3_client = get_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=filename)
        logger.info(f"File deleted successfully from S3: {filename}")
        return True

    except Exception as e:
        logger.error(f"Error deleting file {filename} from S3: {str(e)}")
        return False


def file_exists_in_s3(filename: str, bucket_name: Optional[str] = None) -> bool:
    """
    Check if a file exists in an S3 bucket.

    Args:
        filename: Name of the file to check
        bucket_name: S3 bucket name (optional, uses default from config)

    Returns:
        bool: True if file exists, False otherwise
    """
    if bucket_name is None:
        bucket_name = AWS_STORAGE_BUCKET_NAME

    if not bucket_name:
        logger.error("No S3 bucket name specified")
        return False

    s3_client = get_s3_client()

    try:
        s3_client.head_object(Bucket=bucket_name, Key=filename)
        return True

    except Exception:
        return False
