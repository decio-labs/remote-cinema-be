
from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from src.rooms.models import RoomMemberRole, RoomState
from src.content.schemas import ContentResponse

import enum

class RoomProvider(str, enum.Enum):
    UPLOAD = 'upload'
    YOUTUBE = 'youtube'

class RoomCreateRequest(BaseModel):
    max_guest: int = Field(10, gt=1, le=50)
    room_code: str = Field("WIEK3SHD")
    provider: RoomProvider = Field(default=RoomProvider.UPLOAD)
    link: Optional[str] = None
    upload_content_id: Optional[uuid.UUID] = None
    
class JoinRequest(BaseModel):
    room_code: str = Field(default="unique_room_code", min_length=8, max_length=8)

class RoomMemberResponse(BaseModel):
    member_id: uuid.UUID
    email: Optional[str]
    role: RoomMemberRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class RoomResponse(BaseModel):
    room_id: uuid.UUID
    room_code: str
    host: RoomMemberResponse
    room_state: RoomState
    movie_id: str | None = None
    movie_link: str | None = None
    provider: RoomProvider
    playback_position: float
    is_active: bool
    max_guests: int
    no_guest: int
    member_count: int
    content: ContentResponse | None = None
    members: list[RoomMemberResponse]
    chats: list
    created_at: datetime

    model_config = {"from_attributes": True}
    