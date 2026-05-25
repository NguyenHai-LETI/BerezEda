import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

# Import the association model
from apps.lockers.models.shop_locker_association import ShopLockerAssociation


class Shop(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    owner_id: str = Field(foreign_key="user.id", index=True)
    code: str = Field(index=True, max_length=15, unique=True)
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    address: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=20)
    logo: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True)
    position: Optional[str] = Field(
        default=None, description="Geographic location of the shop"
    )
    avg_rating: float = Field(
        default=0, description="Average rating of reviews for this shop."
    )
    total_reviews: int = Field(
        default=0, description="Total number of reviews for this shop."
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    products_master: List["ProductMaster"] = Relationship(back_populates="shop")  # type: ignore
    combos: List["Combo"] = Relationship(back_populates="shop")  # type: ignore
    owner: Optional["User"] = Relationship(back_populates="owned_shop", sa_relationship_kwargs={"foreign_keys": "Shop.owner_id"})  # type: ignore
    staff_members: List["User"] = Relationship(back_populates="shop", sa_relationship_kwargs={"foreign_keys": "User.shop_id"})  # type: ignore
    favorite: List["Favorite"] = Relationship(back_populates="shop")  # type: ignore
    locker_locations: List["LockerLocation"] = Relationship(  # type: ignore
        back_populates="shops", link_model=ShopLockerAssociation
    )
    reviews: List["Review"] = Relationship(back_populates="shop")  # type: ignore

    def get_all_shop_users(self) -> List["User"]:  # type: ignore
        """
        Get all users associated with this shop (owner + active staff members).

        Returns:
            List[User]: List of User objects (owner + staff)
        """
        users = []

        # Add shop owner
        if self.owner:
            users.append(self.owner)

        # Add active staff members
        if self.staff_members:
            active_staff = [
                staff
                for staff in self.staff_members
                if staff.is_active and staff.permissions == "staff_shop"
            ]
            users.extend(active_staff)

        # Remove duplicates by user ID and return
        seen_ids = set()
        unique_users = []
        for user in users:
            if user.id not in seen_ids:
                seen_ids.add(user.id)
                unique_users.append(user)

        return unique_users

    def get_all_users_favoriting_shop(self) -> List["User"]:  # type: ignore
        """
        Get all users who have favorited this shop.

        Returns:
            List of users who favorited the shop
        """
        if not self.favorite:
            return []

        # Remove duplicates by user ID
        seen_ids = set()
        unique_users = []
        for favorite in self.favorite:
            if favorite.user and favorite.user.id not in seen_ids:
                seen_ids.add(favorite.user.id)
                unique_users.append(favorite.user)

        return unique_users
