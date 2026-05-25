from typing import List, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from apps.auth.permissions import AuthenticatedUser
from apps.core.schemas import ErrorResponse, SuccessResponse

from .s3 import upload_file_to_s3

router = APIRouter(tags=["aws-s3"])


@router.post("/upload-image", response_model=SuccessResponse)
def upload_image_to_s3_api(
    user: AuthenticatedUser,
    file: UploadFile = File(...),
):
    try:
        filename = file.filename or "uploaded_image"
        s3_key = f"images/{filename}"
        file_url = upload_file_to_s3(file.file, s3_key)
        return SuccessResponse(data={"url": file_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.post("/upload-multiple", response_model=SuccessResponse)
def upload_multiple_files(
    user: AuthenticatedUser,
    files: List[UploadFile] = File(...),
    download: Union[str, None] = Query(
        None, description="Set to '1' for download mode"
    ),
) -> Union[ErrorResponse, SuccessResponse]:
    """
    Upload multiple files to S3.
    Supports images (gif, png, jpg, jpeg) and PDF files.
    """
    is_download = download == "1"

    # File extension to content type mapping
    content_type_mappings = {
        "gif": "image/gif",
        "png": "image/png",
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }

    response_data = []

    for file in files:
        # Validate file has a name and extension
        if not file.filename:
            return ErrorResponse(message="ファイル名が見つかりません。")

        # Get file extension
        file_extension = file.filename.split(".")[-1].lower()

        # Determine content type
        if is_download:
            content_type = "binary/octet-stream"
        else:
            content_type = content_type_mappings.get(file_extension)

        if not content_type:
            return ErrorResponse(message="ファイル形式が間違いました。")

        try:
            # Generate S3 key
            s3_key = f"uploads/{file.filename}"

            # Upload file to S3
            file_url = upload_file_to_s3(file.file, s3_key)
            response_data.append(file_url)

        except Exception as e:
            return ErrorResponse(message=f"Upload failed: {str(e)}")

    return SuccessResponse(data=response_data, message="Upload Successful")
