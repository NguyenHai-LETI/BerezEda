from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import desc
from sqlmodel import Session, select

# Import model registry to ensure all relationships are properly configured
from apps.core.models import *  # noqa
from apps.mynaportal.models.myna_authorizer import MynaAuthorizer
from apps.mynaportal.models.user_welfare_support import UserWelfareSupport


def get_myna_authorizer_by_process_id(db: Session, process_id: str):
    statement = select(MynaAuthorizer).where(MynaAuthorizer.processId == process_id)
    return db.exec(statement).first()


def get_max_state(db: Session):
    statement = select(MynaAuthorizer).order_by(desc(MynaAuthorizer.state))  # type: ignore
    obj = db.exec(statement).first()
    state_val = getattr(obj, "state", None) if obj else None
    if not state_val:
        return 0
    return int(state_val)


def create_myna_authorizer(db: Session, data: dict):
    obj = MynaAuthorizer(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_myna_authorizer_status(db: Session, process_id: str, status: str):
    obj = get_myna_authorizer_by_process_id(db, process_id)
    if obj:
        obj.status = status
        obj.updated_at = datetime.now(timezone.utc)
        db.add(obj)
        db.commit()
    return obj


def get_myna_authorizer_by_state(db: Session, state: str):
    """Get MynaAuthorizer by state."""
    statement = select(MynaAuthorizer).where(MynaAuthorizer.state == state)
    return db.exec(statement).first()


def get_myna_authorizer_by_state_and_status(db: Session, state: str, status: str):
    """Get MynaAuthorizer by state and status."""
    statement = select(MynaAuthorizer).where(
        MynaAuthorizer.state == state, MynaAuthorizer.status == status
    )
    return db.exec(statement).first()


def update_myna_authorizer(db: Session, authorizer: MynaAuthorizer):
    """Update an existing MynaAuthorizer."""
    authorizer.updated_at = datetime.now(timezone.utc)
    db.add(authorizer)
    db.commit()
    db.refresh(authorizer)
    return authorizer


# ============================================================================
# UserWelfareSupport CRUD functions
# ============================================================================


def delete_user_welfare_supports_by_user_id(db: Session, user_id: str) -> int:
    """
    Delete all welfare support records for a user.
    """
    statement = select(UserWelfareSupport).where(UserWelfareSupport.user_id == user_id)
    records = list(db.exec(statement).all())
    count = len(records)
    for record in records:
        db.delete(record)
    db.commit()
    return count


def create_user_welfare_supports(
    db: Session,
    user_id: str,
    welfare_types: List[Dict[str, str]],
    myna_authorizer_id: Optional[str] = None,
) -> List[UserWelfareSupport]:
    """
    Create welfare support records for a user.
    Deletes existing records first to ensure fresh data.
    """
    # Delete existing records for this user
    delete_user_welfare_supports_by_user_id(db, user_id)

    # Create new records
    created_records: List[UserWelfareSupport] = []
    for welfare_data in welfare_types:
        support = UserWelfareSupport(
            user_id=user_id,
            welfare_type=welfare_data["message"],
            start_date=welfare_data["start_date"],
            end_date=welfare_data["end_date"],
            myna_authorizer_id=myna_authorizer_id,
        )
        db.add(support)
        created_records.append(support)

    db.commit()
    for record in created_records:
        db.refresh(record)

    return created_records


def get_user_welfare_supports(db: Session, user_id: str) -> List[UserWelfareSupport]:
    """
    Get all welfare supports for a user.
    """
    statement = (
        select(UserWelfareSupport)
        .where(UserWelfareSupport.user_id == user_id)
        .order_by(desc(UserWelfareSupport.created_at))
    )
    return list(db.exec(statement).all())
