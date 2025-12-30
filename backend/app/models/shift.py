from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Shift(SQLModel, table=True):
    ''' A scheduled shift for a single user inside a restaurant.
     Notes:
    - `start_at` and `end_at` are full datetimes (not just time-of-day).
    - Cross-midnight is naturally supported by end_at being on the next day.
    - Store timestamps in UTC to avoid DST bugs (Poland has DST).
    '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    restaurant_id: UUID = Field(foreign_key='restaurant.id', index=True)
    user_id: UUID = Filed(foreign_key='user.id', index=True)
    start_at: datetime = Field(index=True)
    end_at: datetime = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )