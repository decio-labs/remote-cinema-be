from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import String, DECIMAL, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, BIGINT

from src.models.base import Base

import uuid
import enum
from decimal import Decimal
from datetime import datetime


class Plan(Base):
    __tablename__ = "plans"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, 
        index=True, unique=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(
        String(length=300), nullable=True, 
    )

    price: Mapped[Decimal] = mapped_column(
        DECIMAL(), nullable=False, index=True
    ) 
    storage_limit_mb: Mapped[int] = mapped_column(
        BIGINT(), nullable=False, index=True
    )
    is_default: Mapped[bool] = mapped_column(
        nullable=False, default=False, index=True
    )
    is_daily: Mapped[bool] = mapped_column(
        default=False, index=True, nullable=True
    )
    is_monthly: Mapped[bool] = mapped_column(
        default=False, index=True, nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), 
        index=True, 
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), index=True
    )

    subscriptions = relationship("Subscription", cascade="all, delete", back_populates="plans")
    payments  = relationship("Payment", cascade="all, delete", back_populates="plans")

    def __repr__(self):
        return f" Plan = {self.name} <-> {self.storage_limit_mb}"



class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELED = "canceled"
    EXPIRED = "expired"


class Subscription(Base):

    __tablename__ = "subscriptions"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, 
        index=True, unique=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.plan_id")
    )
    status: Mapped[str] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, 
        nullable=False, index=True
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    owner = relationship("UserModel", back_populates="subscriptions")
    plans = relationship("Plan", back_populates="subscriptions")


    def __repr__(self):
        return f" Subscriptions = {self.subscriptin_id} <-> {self.status}"
    

class Status(enum.Enum):
    Pending = 'pending'
    Success = "success"
    Failed = "failed"
    Refunded = 'refunded'


class Payment(Base):
    __tablename__ = "payments"
    
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, 
        default=uuid.uuid4,  unique=True, index=True
        )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.plan_id")
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(), nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(
        String(), default="NGN"
    )
    status: Mapped[str] = mapped_column(
        Enum(Status), default=Status.Pending, index=True
    )

    reference: Mapped[str] = mapped_column(
        String(), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user = relationship("UserModel", back_populates="payments")
    plans = relationship("Plan", back_populates="payments")