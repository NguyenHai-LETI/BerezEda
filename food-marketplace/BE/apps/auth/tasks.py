from datetime import datetime, timezone

from sqlmodel import delete

from apps.auth.models.revoked_token import RevokedToken
from apps.core.celery_app import celery_app
from apps.core.database import get_session


@celery_app.task(name="auth.cleanup_revoked_tokens")
def cleanup_revoked_tokens(batch_size: int = 2000):
    db = next(get_session())
    try:
        now = datetime.now(timezone.utc)
        stmt = delete(RevokedToken).where(RevokedToken.expires_at < now)
        # Some DBs ignore LIMIT on DELETE via ORM; keep full delete for simplicity
        db.exec(stmt)
        db.commit()
    finally:
        db.close()
