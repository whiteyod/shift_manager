from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.restaurant import Restaurant, RestaurantMembership, RestaurantRole
from app.models.user import User


router = APIRouter(tags=['restaurants'])


@router.post('/restaurants', status_code=status.HTTP_201_CREATED)
def create_restaurant(
    *,
    name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    ''' Create a restaurant and make the creator an owner. '''
    if not name.strip():
        raise HTTPException(status_code=422, detail='name is required')
    restaurant = Restaurant(name=name.strip())
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)
    membership = RestaurantMembership(
        restaurant_id=restaurant.id,
        user_id=current_user.id,
        role=RestaurantRole.OWNER
    )
    session.add(membership)
    session.commit()

    return {'id': str(restaurant.id), 'name': restaurant.name}


@router.get('/restaurants')
def list_my_restaurants(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[dict]:
    ''' List restaurants the current user belongs to. '''
    stmt = (
        select(Restaurant, RestaurantMembership)
        .join(
            RestaurantMembership,
            RestaurantMembership.restaurant_id == Restaurant.id
        ).where(RestaurantMembership.user_id == current_user.id)
    )
    rows = session.exec(stmt).all()

    return [
        {
            'id': str(restaurant.id),
            'name': restaurant.name,
            'role': membership.role.value,
        }
        for (restaurant, membership) in rows
    ]