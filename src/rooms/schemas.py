
from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from src.rooms.models import RoomMemberRole, RoomState


class RoomCreateRequest(BaseModel):
    max_guest: int = Field(10, gt=1, le=50)

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
    playback_position: float
    is_active: bool
    max_guests: int
    no_guest: int
    member_count: int
    members: list[RoomMemberResponse]
    chats: list
    created_at: datetime

    model_config = {"from_attributes": True}
    