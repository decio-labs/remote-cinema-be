from fastapi import APIRouter, Request, Depends, HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import MessageReqeust, MessageResponse
from ..config.database import get_db
from ..services.helpers.dependencies import get_sub
from ..rooms.security import is_room_member
from .services import create_chat_message, list_chats

from uuid import UUID

router = APIRouter(tags=['chats'], prefix="/room/chats")


@router.post("", status_code=201, response_model=MessageResponse)
async def send_message_endpoint(
    request: Request, message_request: MessageReqeust, room_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    session_key = request.headers.get("Session-Key", None)
    token = request.headers.get("Authorization", None)
    if token:
        user_id = UUID(await get_sub(token.split(" ")[1]))
    if not user_id:
        user_id = session_key

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='authorization or session-key must be present')
    try:
        if not await is_room_member(room_id, user_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not permitted to perform this action')
        result = await create_chat_message(
            message=message_request.message, user_id=user_id, room_id=room_id, db=db
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("", status_code=200)
async def list_chats_enpoint(
    request: Request, room_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    session_key = request.headers.get("Session-Key", None)
    token = request.headers.get("Authorization", None)
    user_id = None
    if token:
        user_id = UUID(await get_sub(token.split(" ")[1]))
    if not user_id:
        user_id = session_key

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='authorization or session-key must be present')
    try:
        if not await is_room_member(room_id, user_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not permitted to perform this action')
        result = await list_chats(room_id, db)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
