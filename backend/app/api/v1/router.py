from fastapi import APIRouter
from app.api.v1.health import router as health_router

health_router = APIRouter()
router.include_router(health_router, prefix='/v1')