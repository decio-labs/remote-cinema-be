from src.services.users.user_service import UserService, user_service
from src.models.users.auth import UserModel
from src.services.users.jwt_service import TokenService

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import ExpiredSignatureError, JWTError

from uuid import UUID

security = HTTPBearer()

class GetUser:

    async def __call__(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security),
        user_service: UserService = Depends(user_service)
    ) -> UserModel:

        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid authentication scheme"
            )

        token = credentials.credentials

        # decode Token
        try:
            token_service = TokenService()
            payload = await token_service.decode_access_token(token)
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Access token has expired")
        except JWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid access token"+ str(exc))

        #user instance
        user_id = payload.get("sub")

        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if not user.is_active or not user.is_verified:
            raise HTTPException(status_code=403, detail="User account inactive/unverified")
        
        return user
    

get_current_user = GetUser()

