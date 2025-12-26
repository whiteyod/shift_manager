from __future__ import annotations
from dataclasses import field
from datetime import datetime, timezone
from enum import unique
from operator import index
from uuid import UUID, uuid4
import uuid
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    ''' Represents an authenticated person in the system.
    Notes:
    - Phone is the primary identifier OTP login.
    - We keep created_at for auditability and debugging.
    '''
    id: UUID = Field(default_factory=uuid, primary_key=True, index=True)
    phone_e164: str = Field(
        index=True,
        unique=True,
        max_length=20,
        description='Phone number in E.164 format, e.g. +48123123123'
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    