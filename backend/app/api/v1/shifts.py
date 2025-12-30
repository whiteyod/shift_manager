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


def _utc_native(dt: datetime) -> datetime:
    ''' Normalize datetime for DB comparisons.
     Why:
    - Your DB columns are currently TIMESTAMP WITHOUT TIME ZONE,
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


def _require_manage_shifts(membership: RestaurantMembership) -> None:
    ''' Only OWNER/MANAGER can create shifts. '''
    if membership.role not in {RestaurantRole.OWNER, RestaurantRole.MANAGER}:
        raise HTTPException(
            status_code=403,
            detail='Not enough permissions'
        )


# ----------------------- Shifts API endpoints -------------------------

# Create a shift
