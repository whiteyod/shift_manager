from __future__ import annotations
from datetime import datetime, timedelta, timezone
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

    return jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)
    

