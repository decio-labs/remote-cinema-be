from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from .models import _generate_code, Room, RoomMember, RoomMemberRole, RoomState
from .schemas import RoomMemberResponse, RoomResponse
from ..chats.schemas import MessageResponse
from ..chats.models import Chat
from ..content.crud import content_service
from ..content.schemas import ContentResponse

from cachetools import cached, TTLCache
import uuid
import logging


logger = logging.getLogger('uvicorn.error')
cache = TTLCache(maxsize=128, ttl=60)

async def _get_room_by_code(room_code: str, db: AsyncSession):
    stmt = select(Room).where(Room.room_code == room_code, Room.is_active == True).options(
        selectinload(Room.members)
    )
    response = await db.execute(stmt)
    room = response.scalar_one_or_none()
    if not room:
        logger.error("Room not found with code: %s", room_code)
        raise Exception("Room not found")
    logger.info("Fetched room by code: %s", room.__str__())
    return room

@cached(cache)
async def _active_room_id(room_id: uuid.UUID, db: AsyncSession):
    stmt = select(Room).where(Room.room_id == room_id, Room.is_active == True)
    result = await db.execute(stmt)
    room = result.scalar_one_or_none()
    if not room:
        logger.info("Room not found for id %s", room_id)
        raise Exception("Room not found")
    return room

@cached(cache)
async def _get_room_with_members(room_id: uuid.UUID, db: AsyncSession):
    stmt =  select(Room).where(Room.room_id == room_id).options(
        selectinload(Room.members).selectinload(RoomMember.user),
        selectinload(Room.host), selectinload(Room.chats).selectinload(Chat.user),
        selectinload(Room.content)
    )

    response = await db.execute(stmt)
    room = response.scalar_one_or_none()
    if not room:
        logger.error("Room not found with ID: %s", room_id)
        raise Exception("Room not found")
    logger.info("Fetched room with members: %s", room.__str__())
    return room

def _serialize_room(room: Room):
    return RoomResponse(
        room_id=room.room_id,
        room_code=room.room_code,
        host=RoomMemberResponse(
            member_id=room.host.user_id,
            email=room.host.email,
            role=RoomMemberRole.HOST,
            joined_at=room.created_at
        ),
        room_state=room.room_state,
        movie_id=room.movie_id,
        movie_link=room.movie_link,
        provider=room.provider,
        playback_position=room.playback_position,
        is_active=room.is_active,
        max_guests=room.max_guest,
        no_guest=room.no_guest,
        member_count=len(room.members),
        content=ContentResponse(
            content_id=room.content.content_id,
            title=room.content.title,
            description=room.content.description,
            url=room.content.url,
            r2_key=room.content.r2_key,
            thumbnail_url=room.content.thumbnail_url,
            file_size=room.content.file_size,
            duration=room.content.duration,
            content_type=room.content.content_type, 
            created_at=room.content.created_at
        ) if room.content_id else None,
        members=[
            RoomMemberResponse(
                member_id=member.member_id,
                email=member.user.email if member.user else None,
                role=member.role,
                joined_at=member.joined_at
            ) for member in room.members
        ],
        chats=[
            MessageResponse(
                chat_id=chat.chat_id, session_key=chat.session_key, user_id=chat.user_id,
                created_at=chat.created_at, message=chat.message
            )
            for chat in room.chats
        ],
        created_at=room.created_at
    )

async def create_room(
        user_id: uuid.UUID, max_guest:int, db: AsyncSession, link: str = None, content_id: uuid.UUID = None,
        video_id: str = None, provider: str = 'upload', room_code: str = None
    ):
    existing = await db.execute(select(Room).where(Room.room_code == room_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='invalid room code')
        
    if content_id:
        content = await content_service(db).get_content(user_id, content_id)
        if not content:
            raise HTTPException(status_code=404, detail="no upladed content was found")
    
    room = Room(
        room_code=room_code, host_id=user_id, content_id=content_id, max_guest=max_guest,
        movie_id=video_id, movie_link=link, provider=provider
    )      
    db.add(room)
    logger.info("Created room: %s", room.__str__())
    await db.flush()  

    room_member = db.add(RoomMember(user_id=user_id, room_id=room.room_id, role=RoomMemberRole.HOST))
    await db.commit()
    logger.info("Added host to room members: %s", room_member.__str__())

    room = await _get_room_with_members(room.room_id, db)
    return _serialize_room(room)

async def join_room(room_code: str, user_id: uuid.UUID, db: AsyncSession, session_key: str):
    room: Room = await _get_room_by_code(room_code, db)

    if len(room.members) >= room.max_guest:
        logger.warning("Room is full: %s", room.__str__())
        raise HTTPException(status_code=400, detail="Room is full")
    
    existing_member = await db.execute(select(RoomMember).where(RoomMember.room_id == room.room_id, RoomMember.user_id == user_id))
    if not existing_member.scalar_one_or_none():
        room_member = RoomMember(user_id=user_id, room_id=room.room_id, role=RoomMemberRole.VIEWER, session_key=session_key)
        db.add(room_member)
        await db.execute(update(Room).where(Room.room_id == room.room_id).values(no_guest=Room.no_guest + 1))

        await db.commit()

    logger.info("User joined room: %s", room.__str__())
    room = await _get_room_with_members(room.room_id, db)
    return _serialize_room(room)

async def leave_room(room_id: uuid.UUID, user_id: uuid.UUID | None, db: AsyncSession, session_key: str | None):
    room: Room = await _active_room_id(room_id, db)
    member = None
    if user_id:
        if room.host_id == user_id:
            # end room 
            await db.execute(
                update(Room).where(Room.room_id == room_id, is_active=True)
                .values(Room.room_state == RoomState.ENDED, Room.is_active == False)
            )

        result = await db.execute(
            select(RoomMember).where(
                RoomMember.room_id == room_id, RoomMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
    else:
        if session_key:
            result = await db.execute(
                select(RoomMember).where(
                    RoomMember.room_id == room_id, RoomMember.session_key == session_key
                )
            )
            member = result.scalar_one_or_none()

    if member:
        await db.delete(member)
        await db.commit()
    else:
        return {"status": True, "details": "You are not in this room"}

    return { "status": True, "details": "user left this room"}

async def get_room_detail(room_id: uuid.UUID, db: AsyncSession):
    try:
        room = await _get_room_with_members(room_id, db)
        return _serialize_room(room)
    except Exception as exc:
        return HTTPException(status_code=500, detail=str(exc))