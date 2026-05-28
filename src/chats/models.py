from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ( String, UUID, ForeignKey, DateTime)
from sqlalchemy.sql import func

from datetime import datetime

import uuid

class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4(), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.room_id"), nullable=False)
    session_key: Mapped[str] = mapped_column(String(), nullable=True)
    message: Mapped[str] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    room = relationship("Room", back_populates="chats")
    user = relationship("UserModel", back_populates='chats')