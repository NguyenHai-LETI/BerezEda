from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import ShopOwnerOrAdminUser, AuthenticatedUserOrNone
from apps.products import crud, services
from apps.products.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("", response_model=ListResponse[ProductResponse])
def list_my_products(current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)
    products = crud.get_products_by_shop(db, shop.id, active_only=True)
    return ListResponse(data=products, total=len(products))


@router.get("/{product_id}", response_model=SuccessResponse[ProductResponse])
def get_product(product_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    product = services.get_product_or_404(db, product_id)
    return SuccessResponse(data=product)


@router.post("", response_model=SuccessResponse[ProductResponse], status_code=201)
def create_product(body: ProductCreate, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    product = services.create_product(db, current_user.id, body.model_dump())
    return SuccessResponse(data=product, message="Товар создан")


@router.put("/{product_id}", response_model=SuccessResponse[ProductResponse])
def update_product(
    product_id: str,
    body: ProductUpdate,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    product = services.update_product(db, product_id, current_user.id, body.model_dump(exclude_none=True))
    return SuccessResponse(data=product, message="Товар обновлён")


@router.delete("/{product_id}", response_model=SuccessResponse)
def delete_product(product_id: str, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    services.update_product(db, product_id, current_user.id, {"is_active": False})
    return SuccessResponse(message="Товар удалён")


@router.post("/{product_id}/image", response_model=SuccessResponse[ProductResponse])
async def upload_image(
    product_id: str,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    product = await services.upload_product_image(db, product_id, current_user.id, file)
    return SuccessResponse(data=product, message="Изображение загружено")
