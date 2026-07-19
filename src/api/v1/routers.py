from fastapi import APIRouter

from .endpoints import auth_endpoints
from src.content.api import router as content_router
from src.rooms.api import router as rooms_router
from src.chats.api import router as chats_router
from src.plans.api import router as plans_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_endpoints.router)
api_router.include_router(content_router)
api_router.include_router(rooms_router)
api_router.include_router(chats_router)
api_router.include_router(plans_router)


