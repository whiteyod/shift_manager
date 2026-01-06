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
from app.api.v1.shifts import _require_manager_permission, _require_membership


router = APIRouter(tags=['availability'])


# ------------------------- Availability API endpoints ------------------------

# Request availability from the employee
@router.post('/restaurants/{restaurant_id}/availability/requests')
def request_availability(
    *,
    restaurant_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    year: int,
    month: int,
    closes_at_utc: datetime,
    opens_at_utc: datetime = lambda: datetime.now(timezone.utc),
) -> dict:
    ''' Owner or Manager sends a request to eployee to get their availability.
    '''
    check_membership = _require_membership(
        session=session,
        restaurant_id=restaurant_id,
        user_id=current_user.id)
    _require_manager_permission(check_membership)
    year = datetime.now().year


