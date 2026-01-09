from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.restaurant import RestaurantMembership, RestaurantRole
from app.models.shift import Shift
from app.models.user import User


router = APIRouter(tags=['shifts'])


# --------------------------- API helpers -----------------------------


def _utc_native(dt: datetime) -> datetime:
    ''' Normalize datetime for DB comparisons.
     Why:
    - DB columns are currently TIMESTAMP WITHOUT TIME ZONE,
      so values may come back as naive.
    - Comparing naive and aware datetimes raises TypeError.
    '''
    if dt.tzinfo is None:
        return dt

    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _require_membership(
    *,
    session: Session,
    restaurant_id: UUID,
    user_id: UUID
) -> RestaurantMembership:
    ''' Ensure the user belongs to the restaurant. '''
    membership = session.exec(
        select(RestaurantMembership)
        .where(RestaurantMembership.restaurant_id == restaurant_id)
        .where(RestaurantMembership.user_id == user_id)
    ).first()
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail='Not a member of this restaurant'
        )
    
    return membership


def _require_manager_permission(membership: RestaurantMembership) -> None:
    ''' Only OWNER/MANAGER can create shifts. '''
    if membership.role not in {RestaurantRole.OWNER, RestaurantRole.MANAGER}:
        raise HTTPException(
            status_code=403,
            detail='Not enough permissions'
        )


# ----------------------- Shifts API endpoints -------------------------

# Create a shift
@router.post(
    '/restaurants/{restaurant_id}/shifts', status_code=status.HTTP_201_CREATED
)
def create_shift(
    *,
    restaurant_id: UUID,
    user_id: UUID,
    start_at: datetime,
    end_at: datetime,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    ''' Create a shift for a user.
     Validations:
    - Must be a restaurant member (creator must be owner/manager).
    - end_at must be after start_at (cross-midnight allowed if end_at is next day).
    - Prevent overlaps for the same employee inside the restaurant.
    '''
    creator_membership = _require_membership(
        session=session, restaurant_id=restaurant_id, user_id=current_user.id
    )
    _require_manager_permission(creator_membership)
    # Ensure the epmloyee exists in this restaurant
    _require_membership(
        session=session, restaurant_id=restaurant_id, user_id=user_id
    )
    start_cmp = _utc_native(start_at)
    end_cmp = _utc_native(end_at)
    if end_cmp <= start_cmp:
        raise HTTPException(
            status_code=422,
            detail='end_at must be after start_end'
        )
    # Check shifts overlapping
    overpla_stmt = (
        select(Shift)
        .where(Shift.restaurant_id == restaurant_id)
        .where(Shift.user_id == user_id)
        .where(Shift.start_at < end_cmp)
        .where(Shift.end_at > start_cmp)
        .limit(1)
    )
    existing = session.exec(overpla_stmt).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail='Shift overlaps existing shift'
        )
    # Commit all changes to the DB
    shift = Shift(
        restaurant_id=restaurant_id,
        user_id=user_id,
        start_at=start_cmp,
        end_at=end_cmp,
    )
    session.add(shift)
    session.commit()
    session.refresh(shift)

    return {
        'id': str(shift.id),
        'restaurant_id': str(shift.restaurant_id),
        'user_id': str(shift.user_id),
        'start_at': shift.start_at.isoformat(),
        'end_at': shift.end_at.isoformat()
    }


# Get a list of all shifts
@router.get('/restaurants/{restaurant_id}/shifts')
def list_shifts(
    *,
    restaurant_id: UUID,
    start: datetime,
    end: datetime,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[dict]:
    ''' List shifts in a date range for the restaurant.
     Membership:
    - Any restaurant member can read shifts (MVP).
    '''
    _require_membership(
        session=session, restaurant_id=restaurant_id, user_id=current_user.id
    )
    start_cmp = _utc_native(start)
    end_cmp = _utc_native(end)
    if end_cmp <= start_cmp:
        raise HTTPException(
            status_code=422, detail='end must be after start'
        )
    # Range filter
    stmt = (
        select(Shift)
        .where(Shift.restaurant_id == restaurant_id)
        .where(Shift.start_at < end_cmp)
        .where(Shift.end_at > start_cmp)
        .order_by(Shift.start_at.asc())
    )
    shifts = session.exec(stmt).all()

    return [
        {
            'id': str(s.id),
            'user_id': str(s.user_id),
            'start_at': s.start_at.isoformat(),
            'end_at': s.end_at.isoformat(),
        }
        for s in shifts
    ]