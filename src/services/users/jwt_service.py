from src.config.settings import setting
from src.models.users.auth import UserModel, RefreshToken
from src.schemas.users.auth_schemas import TokenPair
from src.services.helpers.hash_management import HashService

from datetime import datetime, time, timedelta, timezone
from jose import JWTError, jwt, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import uuid


class TokenService:
    def __init__(self, user_id: str = None, email: str = None):
        self.user_id = user_id
        self.email = email

    async def create_access_token(self, token_type="access"):

        current_datetime = datetime.now(timezone.utc)
        payload = {
            "sub": self.user_id,
            "email": self.email,
            "role": "user",
            "jti": str(uuid.uuid4()),
            "iat": int(current_datetime.timestamp()),
            "exp": int((current_datetime + timedelta(minutes=setting.JWT_REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
            "token_type": token_type
        }

        return jwt.encode(payload, setting.JWT_SECRET_KEY, algorithm=setting.JWT_ALGORITHM)

    async def create_refresh_token(self, jti, token_type="refresh"):

        current_datetime = datetime.now(timezone.utc)
        payload = {
            "sub": self.user_id,
            "jti": str(jti),
            "iat": int(current_datetime.timestamp()),
            "exp": int((current_datetime + timedelta(days=setting.JWT_REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
            "token_type": token_type
        }

        return jwt.encode(payload, setting.JWT_REFRESH_SECRET_KEY, algorithm=setting.JWT_ALGORITHM)

    async def decode_access_token(self, token: str):
        try:
            payload = jwt.decode(token, setting.JWT_SECRET_KEY, algorithms=[setting.JWT_ALGORITHM])

            if payload.get("token_type") != "access":
                raise JWTError("Invalid token type")
            
            return payload
        
        except ExpiredSignatureError:
            raise JWTError("Token has expired")
        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}")

    async def decode_refresh_token(self, token: str):
        try:
            payload = jwt.decode(token, setting.JWT_REFRESH_SECRET_KEY, algorithms=[setting.JWT_ALGORITHM])

            if payload.get("token_type") != "refresh":
                raise JWTError("Invalid token type")
            
            return payload
        
        except ExpiredSignatureError:
            raise JWTError("Token has expired")
        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}")

class JWTService:

    def __init__(self, user: UserModel, db: AsyncSession):
        self.user = user
        self.token_service = TokenService(user_id=str(user.user_id), email=user.email)
        self.db = db

    async def save_refresh_token(self, refresh_token: str, user_id: str, refresh_id: str, expire_time: datetime):
        refresh_token_hash = HashService.hash_token(refresh_token)
        token = RefreshToken(
            refresh_id=refresh_id,
            user_id=user_id,
            token_hash=refresh_token_hash,
            expires_at=expire_time
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        return token
    
    async def _issue_tokens(self):
       
        jti = uuid.uuid4() # refresh token identifier for blacklisting

        access_token = await self.token_service.create_access_token()
        refresh_token = await self.token_service.create_refresh_token(jti=jti)

        saved_token = await self.save_refresh_token(
            refresh_token=refresh_token, user_id=str(self.user.user_id), 
            refresh_id=jti, expire_time=datetime.now(timezone.utc) + \
                timedelta(days=setting.JWT_REFRESH_TOKEN_EXPIRE_DAYS))
        
        if not saved_token:
            raise ValueError("Failed to save refresh token")

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def get_refresh_token_by_jti(self, jti: uuid.UUID):
        stmt = select(RefreshToken).where(RefreshToken.refresh_id == jti)
        result = await self.db.execute(stmt)
        token_entry = result.scalar_one_or_none()
        print("Refresh Token", token_entry)
        return token_entry

    async def revoke_refresh_token(self, jti: str):
        token_entry = await self.get_refresh_token_by_jti(uuid.UUID(jti))
        if token_entry:
            token_entry.is_revoked = True
            await self.db.commit()
            await self.db.refresh(token_entry)
        
    async def revoke_all_user_tokens(self, user_id: str):
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        for token in tokens:
            token.is_revoked = True
        
        await self.db.commit()