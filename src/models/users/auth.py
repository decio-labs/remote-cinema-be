from src.models.base  import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, LargeBinary, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from src.config.settings import setting

import uuid
from datetime import datetime, timedelta

class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
                                UUID(as_uuid=True), primary_key=True, 
                                unique=True, index=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(
        String(), index=True, nullable=False, unique=True
    )
    password: Mapped[str] = mapped_column(
        String(), nullable=False, index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean(), index=True, default=False
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean(), index=True, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    otp_codes = relationship("OneTimePassword", cascade="all, delete", back_populates="owner")
    subscriptions = relationship("Subscription", cascade="all, delete", back_populates="owner")

    def __repr__(self):
        return f"UserModel = {self.user_id} <-> {self.created_at}"

class OneTimePassword(Base):

    __tablename__ = "otp_codes"

    otp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, 
        index=True, default=uuid.uuid4, unique=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id"), index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.now() + timedelta(minutes=setting.OTP_Expiry)
    )

    hash_code: Mapped[bytes] = mapped_column(
        LargeBinary(), nullable=False, index=True
    )
    raw_code: Mapped[str] = mapped_column(
        String(), nullable=False, index=True, default="00000"
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean(), default=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), default=True, index=True
    )

    owner = relationship("UserModel", back_populates="otp_codes")

    def __repr__(self):
        return f" OneTimePassword = {self.otp_id} <->  {self.is_active}"
    

    def is_expired(self) -> bool:
    
        current_datetime = datetime.now()
        return current_datetime > self.expires_at
    

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    refresh_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, 
        default=uuid.uuid4, unique=True, index=True
        )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
        )
    
    token_hash: Mapped[str] = mapped_column(String(), nullable=False, unique=True)

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"RefreshToken(id={self.refresh_id}, user_id={self.user_id}, is_revoked={self.is_revoked}, expires_at={self.expires_at})"