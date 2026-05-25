from typing import Optional, List
from sqlmodel import Session, select

from apps.core.utils import utcnow

from apps.products.models import ProductMaster


def get_product_by_id(db: Session, product_id: str) -> Optional[ProductMaster]:
    return db.get(ProductMaster, product_id)


def get_products_by_shop(db: Session, shop_id: str, active_only: bool = True) -> List[ProductMaster]:
    q = select(ProductMaster).where(ProductMaster.shop_id == shop_id)
    if active_only:
        q = q.where(ProductMaster.is_active == True)
    return db.exec(q).all()


def create_product(db: Session, shop_id: str, data: dict) -> ProductMaster:
    product = ProductMaster(shop_id=shop_id, **data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: ProductMaster, data: dict) -> ProductMaster:
    for k, v in data.items():
        setattr(product, k, v)
    product.updated_at = utcnow()
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
