from __future__ import annotations
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User


# This tells fastapi where frontend can obtain tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/v1/auth/otp/vetify')
def get_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(oauth2_scheme)
) -> User:
    ''' Resolve the authenticated user from the Bearer token.
     Why this exists:
    - Keeps auth logic out of every route.
    - Makes it easy to protect endpoints with Depends(get_current_user).
    '''
    payload = decode_access_token(token)
    user_id_str = payload.get('sub')
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token missing \'sub\' claim'
        )
    try: 
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            satus_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid \'sub\' claim in token'
        )
    user = session.exec(select(User).where(User.id == user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or incative'
        )
    return user