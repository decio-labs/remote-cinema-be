from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db
from src.rooms.schemas import JoinRequest, RoomCreateRequest, RoomResponse, RoomProvider
from src.rooms.services import create_room, join_room, leave_room, get_room_detail
from src.services.helpers.dependencies import get_current_user, get_sub
from src.services.users.jwt_service import TokenService
from .dependencies import extract_movie_id, is_valid_youtube_url, is_room_member

import uuid

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("/", response_model=RoomResponse)
async def create_room_endpoint(
    request: RoomCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """ 
        Create room Endpoint where the user can send either the link of the youtube video or 
        the content id of the uploaded movie to create a room.
        support guest users
    """
    content_id = None
    video_id = None
    try:
        provider = request.provider
        if provider == RoomProvider.UPLOAD:
            content_id = request.upload_content_id if request.upload_content_id else None
            if content_id is None:
                raise HTTPException(status_code=400, detail="uploaded movie cannot be empty")
        elif provider == RoomProvider.YOUTUBE:
            youtube_movie_url = request.link
            if not await is_valid_youtube_url(youtube_movie_url):
                raise HTTPException(status_code=400, detail='this not a valid youtube url')
    
            video_id = await extract_movie_id(youtube_movie_url)
            if video_id is None:
                raise HTTPException(status_code=400, detail="this url doesn't contain a video ID.")

        room = await create_room(
            user_id=current_user.user_id, max_guest=request.max_guest, db=db, 
            link=request.link, content_id=content_id, video_id=video_id, provider=request.provider,
            room_code=request.room_code
        )
        return room
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/join", response_model=RoomResponse)
async def join_room_endpoint(
    request: Request,
    join_request: JoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """ Endpoint for users to join an existing room using a unique room code.
     support guest users
    """

    guest_user_session_key = request.headers.get("Session-Key", None)

    auth_header = request.headers.get("Authorization", None)
    token = auth_header.split(" ")[1] if auth_header else None
    user_id = await get_sub(token)
    try:
        from uuid import UUID
        room = await join_room(
            room_code=join_request.room_code, user_id=UUID(user_id), db=db, session_key=guest_user_session_key
        )
        return room
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/{room_id}/leave", status_code=200)
async def leave_room_endpoint(
        request: Request,
        room_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    guest_user_session_key = request.headers.get("Session-Key", None)
    auth_header = request.headers.get("Authorization", None)
    token = auth_header.split(" ")[1] if auth_header else None
    user_id = await get_sub(token)
    try:

        result: str = await leave_room(
            room_id, user_id, db, guest_user_session_key
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
@router.get("/{room_id}/detail", response_model=RoomResponse)
async def room_detail_endpoint(
    request: Request, room_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    session_key = request.headers.get("Session-Key", None)
    auth_header = request.headers.get("Authorization", None)
    token = auth_header.split(" ")[1] if auth_header else None
    user_id = await get_sub(token)
    id = None
    if session_key: id = session_key
    if user_id: id = uuid.UUID(user_id)

    if not await is_room_member(room_id, id, db):
        raise HTTPException(status_code=400, detail="You don't have permission to perform this action.")

    return await get_room_detail(room_id, db)