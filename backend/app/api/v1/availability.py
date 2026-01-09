from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_current_user
from app.api.v1.shifts import _require_manager_permission, _require_membership
from app.db.session import get_session
from app.models.availability import AvailabilityRequest, AvailabilityRequestCreate
from app.models.user import User


router = APIRouter(tags=['availability'])


# ------------------------- Availability API endpoints ------------------------

# Request availability from the employee
@router.post(
    '/restaurants/{restaurant_id}/availability/requests',
    status_code=status.HTTP_201_CREATED
)
def request_availability(
    *,
    restaurant_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    payload: AvailabilityRequestCreate
) -> dict:
    ''' Owner or Manager sends a request to eployee to get their availability.
    '''
    check_membership = _require_membership(
        session=session,
        restaurant_id=restaurant_id,
        user_id=current_user.id
    )
    _require_manager_permission(check_membership)
    # Check month range
    # TODO: make an option to request availabilty weekly/two times per month
    if payload.month < 1 or payload.month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='month must be an integer between 1 and 12'
        )
    # Get closes_at date
    closes_at_utc = payload.closes_at_utc
    # Get opens_at date or insert if not set
    opens_at_utc = payload.opens_at_utc or datetime.now(timezone.utc)
    # Check open/close date timezones
    if opens_at_utc.tzinfo is None or closes_at_utc.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='opens_at_utc and closes_at_utc must be timezone-aware datetimes'
        )
    # Normalize datetime timezones into UTC for storage
    opens_at_utc = opens_at_utc.astimezone(timezone.utc)
    closes_at_utc = closes_at_utc.astimezone(timezone.utc)
    # Check is open/close date are not crossing
    if closes_at_utc <= opens_at_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='opens_at must be before closes_at'
        )
    # Prevent availability requests overlapping
    existing = session.exec(
        select(AvailabilityRequest).where(
            AvailabilityRequest.restaurant_id == restaurant_id,
            AvailabilityRequest.year == payload.year,
            AvailabilityRequest.month == payload.month,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Availability request already exists for this restaurant and month'
        )
    # Add request to the session and commit
    req = AvailabilityRequest(
        restaurant_id=restaurant_id,
        year=payload.year,
        month=payload.month,
        opens_at_utc=opens_at_utc,
        closes_at_utc=closes_at_utc,
        created_by_user_id=current_user.id
    )
    session.add(req)
    session.commit()
    session.refresh(req)

    return {
        'id': str(req.id),
        'restaurant_id': str(req.restaurant_id),
        'year': req.year,
        'month': req.month,
        'opens_at_utc': req.opens_at_utc.isoformat(),
        'closes_at_utc': req.closes_at_utc.isoformat(),
        'created_by_user_id': str(req.created_by_user_id)
    }
    

    


