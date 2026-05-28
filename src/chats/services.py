from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Chat
from .schemas import MessageResponse
from ..rooms.services import _get_room_with_members, _serialize_room

from uuid import UUID
from functools import lru_cache
import logging

loggger = logging.getLogger("uvicorn.error")

lru_cache(maxsize=80)
async def _get_chat(chat_id: UUID, db:AsyncSession):
    stmt = select(Chat).where(
        Chat.chat_id == chat_id
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise Exception("message not found")
    return message

async def create_chat_message(message: str, user_id: str | UUID, room_id: UUID, db: AsyncSession):
    chat = Chat(message=message, room_id=room_id)
    if isinstance(user_id, str):
        chat.session_key = user_id
    else:
        chat.user_id = user_id
    
    db.add(chat)
    await db.commit()
    await db.refresh()

    response: Chat = await _get_chat(chat.chat_id, db)
    return MessageResponse(
        message_id=response.chat_id, session_key=response.session_key, 
        user_id=response.user_id, message=response.message, created_at=response.created_at
    )

async def list_chats(room_id: UUID, db: AsyncSession):
    room = await _get_room_with_members(room_id, db)
    return await _serialize_room(room)
