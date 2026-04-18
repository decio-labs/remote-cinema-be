from src.config.database import get_db
from src.services.users.auth_service import  AuthService
from src.services.users.user_service import UserService
from src.services.helpers.dependencies import get_current_user
from src.schemas.users.auth_schemas import (
    RegResponse, RegSchema, ResendOTPSchema, VerifySchema, PasswordResetSchema,
    LoginRequest, RefreshRequest)
from src.models.users.auth import UserModel
from src.services.users.user_service import user_service

from fastapi import Depends, APIRouter, status, HTTPException
from pydantic import ValidationError


from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=['Auth'])

def auth_service(db: AsyncSession = Depends(get_db)):
    return AuthService(db=db)



@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=RegResponse)
async def create_user_router(payload: RegSchema, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))

    return await service.register(payload)

@router.post("/auth/verify", status_code=status.HTTP_200_OK)
async def verify_user_router(payload: VerifySchema, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))

    return await service.verify(payload)

@router.post("/auth/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp_router(payload: ResendOTPSchema, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))

    return await service.resend_otp(payload)


@router.post("/auth/password-reset-request", status_code=status.HTTP_200_OK)
async def password_reset_router(payload: ResendOTPSchema, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))

    return await service.password_reset(payload)

@router.post("/auth/password-reset", status_code=status.HTTP_200_OK)
async def password_reset_confirm_router(payload: PasswordResetSchema, code: str, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))

    return await service.password_reset_confirm(payload, code)


@router.post("/auth/login", status_code=status.HTTP_200_OK)
async def login_router(payload: LoginRequest, service: AuthService = Depends(auth_service)):
    try:
        payload.model_dump()
    except ValidationError as exc:
        return HTTPException(status_code=400, detail=str(exc))
    
    return await service.login(payload)

@router.post("/auth/refresh", status_code=status.HTTP_200_OK)
async def refresh_router(payload: RefreshRequest, service: AuthService = Depends(auth_service)):
    return await service.refresh(payload)


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout_router(service: AuthService = Depends(auth_service),
                        current_user: UserModel = Depends(get_current_user)
                        ):

    return await service.logout(user_id=current_user.user_id)
