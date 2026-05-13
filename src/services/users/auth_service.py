from datetime import datetime, timezone
from jose import JWTError, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.users.auth_schemas import (RegSchema, VerifySchema, 
                                            ResendOTPSchema, PasswordResetSchema,
                                            LoginRequest)
from .user_service import UserService
from .otp_service import OTPService
from ..helpers.hash_management import HashService
from ..helpers.email_service import EmailService
from .jwt_service import JWTService, TokenService

from fastapi import HTTPException, status, BackgroundTasks
from uuid import UUID
import logging

user_service = UserService
otp_service = OTPService
email_service = EmailService
logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.service = user_service(db=db)
        self.otp_service = otp_service(db=db)
        self.email_service = email_service()

    async def register(self, payload: RegSchema, background_tasks: BackgroundTasks):
    
        email, password = payload.email, payload.password
        existing = await self.service.get_user_by_email(email)

        if existing:
            email = existing.email
            name = email.split('@')[0]
            background_tasks.add_task(self.email_service.send_welcome_email,
                name=name, 
                recipient_email=email
            )
            return {"status": True, "detail": "A welcome email has already been sent to this address. Please check your inbox."}
            
        hashed_password = HashService.hash_password(password)
        user = await self.service.create_user(email, hashed_password)

        logger.info("User Created")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create user"
            )
        user_id = user.user_id
        
        otp_code = await self.otp_service.create_and_store_otp(user_id)
        user_email = user.email
        background_tasks.add_task(self.email_service.send_otp_email,
            name=user_email.split('@')[0], 
            otp_code=otp_code, 
            recipient_email=user_email
        )
    
        return {"status": True, "details": "Account registered. Check  your email address for verifications code."}

    async def verify(self, payload: VerifySchema, background_tasks: BackgroundTasks):
        otp_code = payload.otp_code

        is_valid, user_id = await self.otp_service.verify_otp(otp_code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid OTP code"
            )
        user = await self.service.activate_user(user_id)

        # send a confirmation email here
        background_tasks.add_task(self.email_service.send_welcome_email,
            name=user.email.split('@')[0],
            recipient_email=user.email
        )
        # save a default subscription for the user
        # await self.service.save_default_subscription(user_id)
        if user.is_active and user.is_verified:
            subscription_result = await self.service.save_default_subscription(user_id)
            if not subscription_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail="Failed to assign default subscription"
                )
        
        return {"message": "User verified successfully"}
    

    async def resend_otp(self, payload: ResendOTPSchema, background_tasks: BackgroundTasks):
        email = payload.email
        user = await self.service.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Invalid email"
            )
        otp_code = await self.otp_service.create_and_store_otp(user.user_id)
        background_tasks.add_task(self.email_service.send_otp_email,
            name=email.split('@')[0], 
            otp_code=otp_code, 
            recipient_email=email
        )
        return {"message": "OTP resent successfully"}
    
    async def password_reset(self, payload: ResendOTPSchema, background_tasks: BackgroundTasks):
        user_email = payload.email
        
        user = await self.service.get_user_by_email(user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="invalid email address"
            )
        otp_code = await self.otp_service.create_and_store_otp(user.user_id)

        background_tasks.add_task(self.email_service.send_password_reset_email,
            name=user_email.split('@')[0], 
            reset_code=otp_code, 
            recipient_email=user_email
        )

        return {"message": "Password reset instructions sent to your email"}

    async def password_reset_confirm(self, payload: PasswordResetSchema, code: str):

        password, confirm_password = payload.password, payload.confirm_password

        is_valid, user_id = await self.otp_service.verify_otp(code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid or expired reset code"
            )
        
        hashed_password = HashService.hash_password(password)
        user = await self.service.get_user_by_id(user_id)
        try:
            await self.service.set_password(user, hashed_password)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to reset password"
            )
        return {"message": "Password reset successfully"}
        
    async def login(self, payload: LoginRequest):
        email, password = payload.email, payload.password

        user = await self.service.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Invalid credentials"
            )

        if not user.is_active or not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="User account is not active"
            )

        if not HashService.verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid credentials"
            )
        try:
            jwt_service = JWTService(user=user, db=self.service.db)
            tokens = await jwt_service._issue_tokens()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to generate authentication tokens: " + str(e)
            )

        user.last_login = datetime.now()
        await self.service.db.commit()

        return tokens
            
    async def refresh(self, refresh_payload: str):
        
        try:
            service = TokenService()
            refresh_token = await service.decode_refresh_token(refresh_payload.refresh_token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid refresh token: " + str(e)
            )


        jti = refresh_token.get("jti")
        user_id = refresh_token.get("sub")

        user = await self.service.get_user_by_id(UUID(user_id))

        jwt_service = JWTService(user=user, db=self.service.db)
        stored_token = await jwt_service.get_refresh_token_by_jti(UUID(jti))

        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token not recognized"
            )
        
        if stored_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token has expired"
            )
        
        if stored_token.is_revoked:
            # revoke all tokens for the user as a security measure
            await jwt_service.revoke_all_user_tokens(UUID(user_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token has been revoked"
            ) 
        
        if not HashService.verify_token(refresh_payload.refresh_token, stored_token.token_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid refresh token"
            )

        stored_token.is_revoked = True
        await jwt_service.db.commit()

        # issue new tokens
        return await jwt_service._issue_tokens()
    
    async def logout(self, user_id: str):
        user = await self.service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )
        jwt_service = JWTService(user=user, db=self.service.db)
        await jwt_service.revoke_all_user_tokens(user_id)
        return {"message": "Logged out successfully"}
        


        