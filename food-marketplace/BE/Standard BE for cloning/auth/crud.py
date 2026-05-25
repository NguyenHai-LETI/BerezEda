from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from apps.auth.models.revoked_token import RevokedToken


def get_revoked_token_by_jti(db: Session, jti: str) -> Optional[RevokedToken]:
    statement = select(RevokedToken).where(RevokedToken.jti == jti)
    return db.exec(statement).first()


def create_revoked_token(
    db: Session,
    *,
    jti: str,
    user_id: str,
    token_type: str,
    expires_at: datetime,
) -> RevokedToken:
    revoked = RevokedToken(
        jti=jti,
        user_id=user_id,
        token_type=token_type,
        expires_at=expires_at,
    )
    db.add(revoked)
    db.commit()
    db.refresh(revoked)
    return revoked
