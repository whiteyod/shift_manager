from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.models.restaurant import RestaurantRole


def hash_invite_token(token: str) -> str:
    ''' Hash invite token so DB leaks don't expose usable invite links. '''
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def generate_invite_token() -> str:
    ''' Generate a URL-safe random token (raw token returned only once). '''
    return secrets.token_urlsafe(32)


class Invite(SQLModel, table=True):
    ''' Invite to join a restaurant with a specific role. '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    restaurant_id: UUID = Field(foreign_key='restaurant.id', index=True)
    role_to_assign: RestaurantRole = Field(default=RestaurantRole.EMPLOYEE)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    max_uses: int = Field(default=1)
    uses: int = Field(default=0)
    created_by_user_id: UUID = Field(foreign_key='user.id', index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def is_active(self, now: datetime) -> bool:
        ''' Whether the invite can still be used. '''

        # Postgres columns are currently created as TIMESTAMP WITHOUT TIME ZONE,
        # so values loaded from DB may be offset-naive.
        # Normalize both sides to UTC-naive before comparing.
        expires_at = self.expires_at

        if now.tzinfo is not None:
            now_cmp = now.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            now_cmp = now

        if expires_at.tzinfo is not None:
            expires_cmp = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            expires_cmp = expires_at

        return self.uses < self.max_uses and expires_cmp > now_cmp