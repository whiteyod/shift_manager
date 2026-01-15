from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Optional, List
from uuid import UUID, uuid4
import sqlalchemy as sa
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
    __table_args__ = (
        sa.UniqueConstraint(
            'restaurant_id',
            'year',
            'month',
            name='uq_availabilityrequest_restaurant_year_month',
        ),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    restaurant_id: UUID = Field(foreign_key='restaurant.id', index=True)
    year: int = Field(index=True)
    month: int = Field(index=True)
    opens_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=sa.Column(sa.DateTime(timezone=True), index=True, nullable=False),
    )
    closes_at_utc: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), index=True, nullable=False)
    )
    created_by_user_id: UUID = Field(foreign_key='user.id', index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )


class AvailabilitySubmission(SQLModel, table=True):
    """Employee submission for a specific availability request."""
    __table_args__ = (
        sa.UniqueConstraint(
            'request_id',
            'user_id',
            name='uq_availabilitysubmission_request_user',
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted') OR status IS NULL",
            name='ck_availabilitysubmission_status_valid',
        ),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    request_id: UUID = Field(
        foreign_key='availabilityrequest.id', index=True
    )
    user_id: UUID = Field(foreign_key='user.id', index=True)
    submitted_at_utc: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), index=True, nullable=True),
    )
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
