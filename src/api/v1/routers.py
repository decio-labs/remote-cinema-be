from fastapi import APIRouter

from .endpoints import auth_endpoints

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_endpoints.router)


