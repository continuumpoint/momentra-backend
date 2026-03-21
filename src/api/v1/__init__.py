from fastapi import APIRouter
from src.api.v1.routes import auth, events, photos

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(photos.router)
