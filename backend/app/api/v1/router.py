from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.health_db import router as health_db_router
from app.api.v1.auth import router as auth_router
from app.api.v1.me import router as me_router
from app.api.v1.restaurants import router as restaurants_router
from app.api.v1.invites import router as invites_router
from app.api.v1.shifts import router as shifts_router
from app.api.v1.availability import router as availability_router


router = APIRouter()


router.include_router(health_router, prefix='/v1')
router.include_router(health_db_router, prefix='/v1')
router.include_router(auth_router, prefix='/v1')
router.include_router(me_router, prefix='/v1')
router.include_router(restaurants_router, prefix='/v1')
router.include_router(invites_router, prefix='/v1')
router.include_router(shifts_router, prefix='/v1')
router.include_router(availability_router, prefix='/v1')
