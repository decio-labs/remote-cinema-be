from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from .models import _generate_code, Room, RoomMember, RoomMemberRole, RoomState
from .schemas import RoomMemberResponse, RoomResponse
from ..chats.schemas import MessageResponse
from ..chats.models import Chat

from functools import lru_cache
import uuid
import logging


logger = logging.getLogger('uvicorn.error')

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

@lru_cache(maxsize=100)
async def _active_room_id(room_id: uuid.UUID, db: AsyncSession):
    stmt = select(Room).where(Room.room_id == room_id, Room.is_active == True)
    result = await db.execute(stmt)
    room = result.scalar_one_or_none()
    if not room:
        logger.info("Room not found for id %s", room_id)
        raise Exception("Room not found")
    return room

@lru_cache(maxsize=100)
async def _get_room_with_members(room_id: uuid.UUID, db: AsyncSession):
    stmt =  select(Room).where(Room.room_id == room_id).options(
        selectinload(Room.members).selectinload(RoomMember.user),
        selectinload(Room.host), selectinload(Room.chats).selectinload(Chat.user)
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
        playback_position=room.playback_position,
        is_active=room.is_active,
        max_guests=room.max_guest,
        no_guest=room.no_guest,
        member_count=len(room.members),
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

async def create_room(user_id: uuid.UUID, max_guest:int, db: AsyncSession):
    while True:
        code = _generate_code()
        existing = await db.execute(select(Room).where(Room.room_code == code))
        if not existing.scalar_one_or_none():
            break
    room = Room(host_id=user_id, room_code=code, max_guest=max_guest)      
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
        if room .host_id == user_id:
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

