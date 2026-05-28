from fastapi import WebSocket, Depends, WebSocketException, status
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.users.jwt_service import TokenService
from src.services.users.user_service import user_service
from src.rooms.models import Room
from sqlalchemy import select

import logging
import uuid

logger = logging.getLogger("uvicorn.error")

@dataclass
class GuestUser:
    id: str # Unique identifier for the guest user, e.g., a UUID
    user_name: str  # Display name for the guest user, can be generated or provided by the client
    is_guest: bool = True
    is_authenticated: bool = False


@dataclass
class AuthenticatedUser:    
    id: str # Unique identifier for the authenticated user, e.g., a UUID
    user_name: str
    is_guest: bool = False
    is_authenticated: bool = True



async def get_websocket_user(websocket: WebSocket = Depends(), db: AsyncSession = Depends()) -> GuestUser | AuthenticatedUser:
    """
    Dependency to extract user information from the WebSocket connection.
    This function checks for authentication tokens and retrieves user info from the database.
    If no valid token is found, it creates a GuestUser instance.
    """
    token = websocket.query_params.get("token")
    if token:
        # extract user info from token
        token_service = TokenService()
        try:
            payload = await token_service.decode_access_token(token)
            user_id = payload.get("sub")
            user = await user_service(db).get_user_by_id(user_id)
            if user and user.is_active and user.is_verified:
                return AuthenticatedUser(id=str(user.user_id), user_name=user.name if user.name else user.email)
        except Exception as exc:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc))
    # If no valid token is found, create a GuestUser instance
    return GuestUser(id=str(uuid.uuid4()), user_name="Guest__" + str(uuid.uuid4())[:8])


async def get_websocket_room(room_code: str, db: AsyncSession) -> Room:
    stmt = select(Room).where(Room.room_code == room_code)
    result = await db.execute(stmt)
    room = result.scalar_one_or_none()
    if not room:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return room
