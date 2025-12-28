from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class RestaurantRole(str, Enum):
    ''' System permission roles (stable). 
    Display names are customizable later.
    '''
    OWNER = 'owner'
    MANAGER = 'manager'
    EMPLOYEE = 'employee'


class Restaurant(SQLModel, table=True):
    ''' A tenant/workspace (one gastronomy business). '''
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(max_length=200, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # memberships: List['RestaurantMembership'] = Relationship(back_populates='restaurant')


class RestaurantMembership(SQLModel, table=True):
    ''' Join table: user belongs to restaurant with a role. '''
    restaurant_id: UUID = Field(foreign_key='restaurant.id', primary_key=True)
    user_id: UUID = Field(foreign_key='user.id', primary_key=True)
    role: RestaurantRole = Field(default=RestaurantRole.EMPLOYEE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # restaurant: Optional[Restaurant] = Relationship(back_populates='memberships')