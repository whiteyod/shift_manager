from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.health_db import router as health_db_router

router = APIRouter()
router.include_router(health_router, prefix='/v1')
router.include_router(health_db_router, prefix='/v1')