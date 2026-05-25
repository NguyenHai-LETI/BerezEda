from typing import Annotated, Optional

from fastapi import Depends

from apps.auth.dependencies import (
    get_admin_user,
    get_authenticated_user,
    get_current_user_or_none,
    get_customer_user,
    get_locker_owner_or_admin_user,
    get_shop_locker_owner_or_admin_user,
    get_shop_owner_or_admin_user,
)
from apps.users.models import User

AdminUser = Annotated[User, Depends(get_admin_user)]
CustomerUser = Annotated[User, Depends(get_customer_user)]
ShopOwnerOrAdminUser = Annotated[User, Depends(get_shop_owner_or_admin_user)]
LockerOwnerOrAdminUser = Annotated[User, Depends(get_locker_owner_or_admin_user)]
ShopLockerOwnerOrAdminUser = Annotated[User, Depends(get_shop_locker_owner_or_admin_user)]
AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]
AuthenticatedUserOrNone = Annotated[Optional[User], Depends(get_current_user_or_none)]
