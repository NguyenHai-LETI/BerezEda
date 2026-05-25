from sqlmodel import Session
from fastapi import UploadFile

from apps.shops import crud
from apps.shops.exceptions import shop_not_found, shop_already_exists, shop_access_denied
from apps.shops.models import Shop
from apps.integrations.file_storage import file_storage


def get_shop_or_404(db: Session, shop_id: str) -> Shop:
    shop = crud.get_shop_by_id(db, shop_id)
    if not shop:
        raise shop_not_found()
    return shop


def create_shop_for_owner(db: Session, owner_id: str, data: dict) -> Shop:
    if crud.get_shop_by_owner(db, owner_id):
        raise shop_already_exists()
    return crud.create_shop(db, owner_id, data)


def update_shop_by_owner(db: Session, shop_id: str, owner_id: str, data: dict, is_admin: bool = False) -> Shop:
    shop = get_shop_or_404(db, shop_id)
    if not is_admin and shop.owner_id != owner_id:
        raise shop_access_denied()
    return crud.update_shop(db, shop, data)


async def upload_shop_image(db: Session, shop_id: str, owner_id: str, file: UploadFile) -> Shop:
    shop = get_shop_or_404(db, shop_id)
    if shop.owner_id != owner_id:
        raise shop_access_denied()
    if shop.image:
        file_storage.delete(shop.image)
    path = await file_storage.upload(file, subfolder="shops")
    return crud.update_shop(db, shop, {"image": path})
