from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.invite import Invite, generate_invite_token, hash_invite_token
from app.models.restaurant import RestaurantMembership, RestaurantRole
from app.models.user import User


router = APIRouter(tags=['invites'])

# Helper to check user permissions
def require_role(
    *,
    session: Session,
    restaurant_id: UUID,
    user_id: UUID,
    allowed: set[RestaurantRole]
) -> None:
    ''' Authorization helper: ensure user has one of allowed roles. '''
    membership = session.exec(
        select(RestaurantMembership)
        .where(RestaurantMembership.restaurant_id == restaurant_id)
        .where(RestaurantMembership.user_id == user_id)
    ).first()
    if membership is None or membership.role not in allowed:
        raise HTTPException(status_code=403, detail='Not enough permissions')


# --------------------------- Invite API endpoints ---------------------------

# Owner creates invite
@router.post(
    '/restaurants/{restaurant_id}/invites',
    status_code=status.HTTP_201_CREATED
)
def create_invite(
    *,
    restaurant_id: UUID,
    role_to_assign: RestaurantRole = RestaurantRole.EMPLOYEE,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    ''' Owner or manager creates an ivite link. '''
    require_role(
        session=session,
        restaurant_id=restaurant_id,
        user_id=current_user.id,
        allowed={RestaurantRole.OWNER}, # TODO: make the manager to create invites too
    )
    raw_token = generate_invite_token()
    now = datetime.now(timezone.utc)
    invite = Invite(
        restaurant_id=restaurant_id,
        role_to_assign=role_to_assign,
        token_hash=hash_invite_token(raw_token),
        expires_at=now + timedelta(days=7),
        max_uses=1,
        created_by_user_id=current_user.id
    )
    session.add(invite)
    session.commit()
    session.refresh(invite)

    return {
        'invite_id': str(invite.id),
        'token': raw_token,
        'expires_at': invite.expires_at.isoformat(),
        'role_to_assign': invite.role_to_assign.value,
    }


# User accepts invite
@router.post('/invites/accept')
def accept_invite(
    *, 
    token: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    ''' Accept invite token and create membership for current user. '''
    now = datetime.now(timezone.utc)
    invite = session.exec(
        select(Invite).where(Invite.token_hash == hash_invite_token(token))
    ).first()
    # Check if invite is valid
    if invite is None or not invite.is_active(now):
        raise HTTPException(
            status_code=400,
            detail='Invite is invalid or expired'
        )
    # Prevent duplicate membership
    existing = session.exec(
        select(RestaurantMembership)
        .where(RestaurantMembership.restaurant_id == invite.restaurant_id)
        .where(RestaurantMembership.user_id == current_user.id)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail='Already a member of this restaurant'
        )
    membership = RestaurantMembership(
        restaurant_id=invite.restaurant_id,
        user_id=current_user.id,
        role=invite.role_to_assign
    )
    invite.uses += 1
    session.add(membership)
    session.add(invite)
    session.commit()

    return {
        'status': 'ok',
        'restaurant_id': str(invite.restaurant_id),
        'role': membership.role.value
    }
    