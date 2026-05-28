from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (UUID, Enum as SAEnum, String, Float, DateTime, BigInteger,
                        ForeignKey)
from sqlalchemy.sql import func

import uuid 
import enum
from datetime import datetime
import string, random


class ContentType(str, enum.Enum):
    VIDEO = "video"
    SHORT = "short"


class Content(Base):

    """Movies/show catalog"""

    __tablename__ = "contents"

    content_id: Mapped[uuid.UUID] = mapped_column(
                                UUID(as_uuid=True), primary_key=True, 
                                unique=True, index=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    content_type: Mapped[str] = mapped_column(SAEnum(ContentType), default=ContentType.SHORT, nullable=False)
    r2_key: Mapped[str] = mapped_column(String(600), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(2500), nullable=False)
    duration: Mapped[float] = mapped_column(Float(), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger(), nullable=True)

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    uploaded_by = relationship("UserModel", back_populates="contents")

    def __str__(self):
        return f"ContentModel = {self.content_id} <-> {self.title} <-> {self.content_type} <-> {self.created_at}"   
    

