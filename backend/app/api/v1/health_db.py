from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session
from app.db.session import get_session


router = APIRouter(tags=['health'])
@router.get('/health/db')
def check_db(session: Session = Depends(get_session)) -> dict:
    session.execute(text('SELECT 1'))
    return {'status': 'ok', 'db': 'ok'}