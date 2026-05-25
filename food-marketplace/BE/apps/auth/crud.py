from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from apps.auth.models.revoked_token import RevokedToken


def get_revoked_token_by_jti(db: Session, jti: str) -> Optional[RevokedToken]:
    return db.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first()


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


def revoke_token(db, jti: str, expires_at=None):
    pass  # Token blacklist handled by RevokedToken model if needed
