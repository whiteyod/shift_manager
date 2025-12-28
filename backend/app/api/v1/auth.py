from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.security import create_access_token
from app.db.session import get_session
from app.models.otp import OtpCode
from app.models.user import User


# Enable routing
router = APIRouter(tags=['auth'])


# PL phone numbers normalization
def _normalize_pl_phone(phone_national: str) -> str:
    ''' Convert `123123123` -> `+48123123123` for PL MVP.
     Assumptions:
    - UI pre-fils `+48`, user types the rest of the number(9 digits).
    '''
    if not phone_national.isdigit() or len(phone_national) != 9:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='phone_national must be exactly 9 digits'
        )

    return '+48' + phone_national


# OTP codes hashing
def _hash_otp(code: str) -> str:
    ''' Hash OTP code to avoid plain text usage.
     Note: 
    - SHA256 for MVP, switch to stronger approach later.
    '''
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


# ------------------- API Endpoints for OTP-code authentication -----------------------

# Send OTP code request
@router.post('/auth/otp/request')
def request_otp(
    *,
    phone_national: str,
    session: Session = Depends(get_session)
) -> dict:
    ''' Request an OTP code via SMS (MVP: log only).
     Flow:
    - Normalize phone (Poland-only).
    - Generate a 6-digit code.
    - Store hash + expiry in DB.
    - Log code (dev only).
    '''
    phone_e164 = _normalize_pl_phone(phone_national)
    # 6-digit numeric code
    code = f'{secrets.randbelow(1_000_000):06d}'
    now = datetime.now(timezone.utc)
    otp = OtpCode(
        phone_e164=phone_e164,
        code_hash=_hash_otp(code),
        expires_at=now + timedelta(minutes=5),
        attempts_left=5
    )
    session.add(otp)
    session.commit()
    # DEV ONLY: simulate SMS sending by logging the code
    # TODO: make call a real SMS provider
    print(f'[DEV OTP] phone={phone_e164} code={code}')
    return {'status': 'ok'}


# Verify OTP code
@router.post('/auth/otp/verify')
def verify_otp(
    *,
    phone_national: str,
    code: str,
    session: Session = Depends(get_session)
) -> dict:
    ''' Verify OTP and issue JWT.
     Flow:
    - Find latest active OTP for phone (not used, not expired, attempts_left > 0)
    - If code wrong: decrement attempts, commit, reject
    - If code correct: mark used, upsert User, issue JWT
    '''
    phone_e164 = _normalize_pl_phone(phone_national)
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='code must be a 6 digits'
        )
    now = datetime.now(timezone.utc)
    stmt = (
        select(OtpCode)
        .where(OtpCode.phone_e164 == phone_e164)
        .where(OtpCode.used_at.is_(None))
        .where(OtpCode.expires_at > now)
        .where(OtpCode.attempts_left > 0)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    otp = session.exec(stmt).first()
    if otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No active OTP found (expired ot not requested)'
        )
    if otp.code_hash != _hash_otp(code):
        otp.attempts_left -= 1
        session.add(otp)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid code'
        )
    otp.used_at = now
    session.add(otp)
    # Upset user by phone number
    user = session.exec(select(User).where(User.phone_e164 == phone_e164)).first()
    if user is None:
        user = User(phone_e164=phone_e164)
        session.add(user)
    session.commit()
    session.refresh(user)
    access_token = create_access_token(subject=str(user.id))
    return {'access_token': access_token, 'token_type': 'bearer'}

