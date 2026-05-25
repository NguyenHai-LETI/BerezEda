from typing import Optional, List
from sqlmodel import Session, select
from apps.users.models.users import User
from apps.core.utils import utcnow


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.exec(select(User).where(User.email == email)).first()


def get_all_users(db: Session) -> List[User]:
    return db.exec(select(User)).all()


def create_user(db: Session, data: dict) -> User:
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: dict) -> User:
    for k, v in data.items():
        setattr(user, k, v)
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.exec(select(User).where(User.username == username)).first()
