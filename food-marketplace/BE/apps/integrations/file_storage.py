import uuid
import os
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from apps.core.config import UPLOAD_DIR, MAX_FILE_SIZE_MB

ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class FileStorageService:
    def __init__(self):
        self.upload_dir = Path(UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, subfolder: str = "general") -> str:
        if file.content_type not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимый тип файла. Разрешены: JPEG, PNG, WebP, GIF",
            )
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Файл слишком большой. Максимум {MAX_FILE_SIZE_MB}МБ",
            )
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        folder = self.upload_dir / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / filename
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)
        return f"{subfolder}/{filename}"

    def delete(self, file_path: str) -> None:
        if not file_path:
            return
        full_path = self.upload_dir / file_path
        if full_path.exists():
            full_path.unlink()

    def get_url(self, file_path: str, base_url: str = "") -> str:
        if not file_path:
            return ""
        if file_path.startswith("http"):
            return file_path
        return f"{base_url}/uploads/{file_path}"


file_storage = FileStorageService()
