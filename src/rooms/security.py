
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..rooms.models import RoomMember

async def is_room_member(room_id: UUID,  user_id: UUID | str, db: AsyncSession):
    result = None
    if isinstance(user_id, str):
        result = await db.execute(select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.session_key == user_id,
        ))
    else:
        result = await db.execute(select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user_id,
        ))
    member = result.scalar_one_or_none()

    if member:
        return True
    return False