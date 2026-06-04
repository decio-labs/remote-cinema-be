import re
import uuid

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RoomMember

async def extract_movie_id(movie_link):
    "function to extract youtube movie id"
    pattern = r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, movie_link)
    return match.group(1) if match else None

async def is_valid_youtube_url(url):
    pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)[a-zA-Z0-9_-]{11}(&.*)?$'
    return bool(re.match(pattern, url))

async def is_room_member(room_id, user_identity, db: AsyncSession) -> RoomMember | None:
    # user_identity can be the user_id or the session_key
    stmt = None

    if isinstance(user_identity, str):
        stmt = select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.session_key == user_identity
        )
    elif isinstance(user_identity, uuid.UUID):
        stmt = select(RoomMember).where(
            RoomMember.room_id==room_id, RoomMember.user_id == user_identity
        )
        
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

