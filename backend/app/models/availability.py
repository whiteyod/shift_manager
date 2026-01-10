from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class AvailabilityRequestCreate(SQLModel):
    """Request body schema for creating a monthly availability request.

    This is kept separate from the DB model to avoid accepting redundant or
    server-managed fields (e.g. id, created_at).
    """
    year: int
    month: int
    closes_at_utc: datetime
    opens_at_utc: datetime | None = None


class AvailabilitySubmissionUpdate(SQLModel):
    """Request body schema for replacing all available days in a submission."""
    available_dates: List[date]


class AvailabilityRequest(SQLModel, table=True):
    """Availability request for a given restaurant and target (year, month).

    - `opens_at_utc` / `closes_at_utc` define the time window when employees
      can submit/update their availability.
    """
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
    """Employee submission for a specific availability request."""
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    request_id: UUID = Field(
        foreign_key='availabilityrequest.id', index=True
    )
    user_id: UUID = Field(foreign_key='user.id', index=True)
    submitted_at_utc: Optional[datetime] = Field(index=True)
    status: Optional[str] = Field(index=True)


class AvailabilityDay(SQLModel, table=True):
    """Selected available days.

    Stored as Warsaw-local calendar dates (DATE) to avoid DST/timezone issues.
    Composite primary key prevents duplicates within a submission.
    """
    submission_id: UUID = Field(
        foreign_key='availabilitysubmission.id', primary_key=True
    )
    date_local: date = Field(primary_key=True, index=True)
