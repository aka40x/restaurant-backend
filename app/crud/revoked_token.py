from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.revoked_token import RevokedToken


def is_revoked(db: Session, jti: str | None) -> bool:
    if not jti:  # token cũ chưa có jti thì coi như chưa thu hồi
        return False
    return db.scalar(select(RevokedToken.id).where(RevokedToken.jti == jti)) is not None


def revoke(db: Session, jti: str, exp_timestamp: int) -> None:
    if is_revoked(db, jti):
        return
    expires_at = datetime.fromtimestamp(exp_timestamp, timezone.utc).replace(tzinfo=None)
    db.add(RevokedToken(jti=jti, expires_at=expires_at))
    db.commit()


def purge_expired(db: Session) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    db.commit()