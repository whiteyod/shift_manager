from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class OtpCode(SQLModel, table=True):
    ''' Stores OTP verification attempts.
     Notes:
    - Store only a hash of the OTP code.
    - Enforece expiry and attempt limits.
    '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    phone_e164: str = Field(index=True, max_length=20)
    code_hash: str
    expires_at: datetime
    attempts_left: int = Field(default=5)
    used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )