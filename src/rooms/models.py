from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import (String, ForeignKey, UUID, 
                        Integer, DateTime, Boolean, Float)


import uuid
import enum
from datetime import datetime


class RoomState(str, enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    PAUSED  = "paused"
    ENDED   = "ended"


class RoomMemberRole(str, enum.Enum):
    HOST   = "host"
    VIEWER = "viewer"

class Room(Base):
    __tablename__ = "rooms"

    room_id: Mapped[uuid.UUID] = mapped_column(
                                UUID(as_uuid=True), primary_key=True, 
                                unique=True, index=True, default=uuid.uuid4)
    room_code: Mapped[str] = mapped_column(String(), index=True, nullable=False, unique=True)
    room_state: Mapped[str] = mapped_column(String(), default=RoomState.WAITING.value, index=True)
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"), index=True)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.content_id"), index=True, nullable=True)
    max_guest: Mapped[int]  = mapped_column(Integer(), default=0, index=True)
    no_guest: Mapped[int] = mapped_column(Integer(), default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)
    playback_position: Mapped[float] = mapped_column(Float(), default=0.00, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    host = relationship("UserModel", back_populates="rooms")
    members = relationship("RoomMember", back_populates='room', cascade="all, delete-orphan")
    content = relationship("Content")
    chats = relationship("Chat", back_populates="room", cascade="all, delete-orphan")

    def __str__(self):
        return f"{self.__class__.__tablename__}: {self.room_id} - {self.room_code} ({self.room_state}) hosted by {self.host_id}"
    
    

class RoomMember(Base):
    __tablename__ = "room_members"

    member_id: Mapped[uuid.UUID] = mapped_column(
                                UUID(as_uuid=True), primary_key=True, 
                                unique=True, index=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.room_id"), index=True
    )
    role: Mapped[str] = mapped_column(String(), default=RoomMemberRole.VIEWER, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id"), index=True, nullable=True
    )
    session_key: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    room = relationship("Room", back_populates="members")
    user = relationship("UserModel")

    def __str__(self):
        return f"{self.__class__.__tablename__}: {self.member_id} - {self.user_id} in room {self.room_id} as {self.role}"

def _generate_code(length=8):
    import random, string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))
