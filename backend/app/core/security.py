from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import jwt
from app.core.config import settings


def create_access_token(*, subject: str) -> str:
    ''' Create a signed JWT access token.
    Why this function exists:
    - Centralizes how tokens are created (one place to change later).
    - Keeps secret + algorithm out of route handlers.
    Claims:
    - sub: who the token belongs to (we store user_id here)
    - exp: when the token expires (UTC)
    '''
    expires_delta = timedelta(minutes=settings.access_token_exp_mins)
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        'sub': subject,
        'exp': expire_at
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)



def decode_access_token(token: str) -> dict:

    try:
        decoded_token = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return decoded_token
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='incorrect access token'
        )
    
    

