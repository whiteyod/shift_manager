from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class AvailabilityRequestCreate(SQLModel):
    ''' Request body schema to avoid putting redudant fields. '''
    year: int
    month: int
    closes_at_utc: datetime
    opens_at_utc: datetime | None = None


class AvailabilityRequest(SQLModel, table=True):
    ''' Owner or manager sends a request to get availability from the employee. '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    restaurant_id: UUID = Field(foreign_key='restaurant.id', index=True)
    year: int = Field(index=True)
    month: int = Field(index=True)
    opens_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    closes_at_utc: datetime = Field(index=True)
    created_by_user_id: UUID = Field(foreign_key='user.id', index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AvailabilitySubmission(SQLModel, table=True):
    ''' Employee submits the days he is available to work. '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    request_id: UUID = Field(
        foreign_key='availabilityrequest.id', index=True
    )
    user_id: UUID = Field(foreign_key='user.id', index=True)
    submitted_at_utc: Optional[datetime] = Field(index=True)
    status: Optional[str] = Field(index=True)


class AvailabilityDay(SQLModel, table=True):
    ''' Selected days. '''
    submission_id: UUID = Field(
        foreign_key='availabilitysubmission.id', primary_key=True
    )
    date_local: date = Field(primary_key=True, index=True)
