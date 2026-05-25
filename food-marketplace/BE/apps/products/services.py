import json

from sqlmodel import Session
from fastapi import UploadFile

from apps.products import crud
from apps.products.exceptions import product_not_found, product_access_denied
from apps.products.models import ProductMaster
from apps.shops.crud import get_shop_by_owner
from apps.shops.exceptions import shop_not_found
from apps.integrations.file_storage import file_storage


def get_my_shop_id(db: Session, owner_id: str) -> str:
    shop = get_shop_by_owner(db, owner_id)
    if not shop:
        raise shop_not_found()
    return shop.id


def get_product_or_404(db: Session, product_id: str) -> ProductMaster:
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise product_not_found()
    return product


def assert_owner(product: ProductMaster, shop_id: str):
    if product.shop_id != shop_id:
        raise product_access_denied()


def create_product(db: Session, owner_id: str, data: dict) -> ProductMaster:
    shop_id = get_my_shop_id(db, owner_id)
    return crud.create_product(db, shop_id, data)


def update_product(db: Session, product_id: str, owner_id: str, data: dict) -> ProductMaster:
    shop_id = get_my_shop_id(db, owner_id)
    product = get_product_or_404(db, product_id)
    assert_owner(product, shop_id)
    return crud.update_product(db, product, data)


async def upload_product_image(db: Session, product_id: str, owner_id: str, file: UploadFile) -> ProductMaster:
    shop_id = get_my_shop_id(db, owner_id)
    product = get_product_or_404(db, product_id)
    assert_owner(product, shop_id)
    path = await file_storage.upload(file, subfolder="products")
    # product.images may be None, a list, or a JSON string from DB
    raw = product.images
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raw = None
    if not isinstance(raw, list):
        raw = []
    new_images = raw + [path]
    return crud.update_product(db, product, {"images": new_images})
