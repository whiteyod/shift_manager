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