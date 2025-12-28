from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(tags=['users'])


@router.get('/me')
def read_me(current_user: User = Depends(get_current_user)) -> dict:
    ''' Return the current authenticated user '''
    return {
        'id': str(current_user.id),
        'phone_e164': current_user.phone_e164,
        'is_active': current_user.is_active,
    }