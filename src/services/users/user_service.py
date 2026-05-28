from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import Depends

from src.models.users.auth import UserModel
from src.models.plans.plans import Plan, Subscription, SubscriptionStatus
from src.config.settings import  get_settings

from datetime import datetime, timedelta, timezone
from src.config.database import get_db

import logging
logger = logging.getLogger("uvicorn.error")

class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.trail_period_days =  get_settings().TRIAL_PERIOD_DAYS
        self.google_id = get_settings().GOOGLE_CLOUD_ID
        self.request_instance = requests.Request()

    async def verify_auth_token(self, token: str):
        try:
            payload = id_token.verify_oauth2_token(
                id_token=token, request=self.request_instance, audience=self.google_id
            )
            return True, payload
        except Exception as exc:
            return False, str(exc)

    async def get_user_by_email(self, email: str):
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id):
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
            self, email: str, hashed_password: bytes = None, provider: str = None, 
            google_id: str = None, profile_picture: str = None, name: str = None
        ):

        new_user = UserModel(
            email=email, password=hashed_password, provider=provider,
            google_id=google_id, profile_picture=profile_picture, name=name
        )
        self.db.add(new_user)
        await self.db.commit()

        await self.db.refresh(new_user)
        return new_user
    
    async def activate_user(self, user_id):
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        if user.is_verified and user.is_active:
            # User is already active and verified, no need to update
            return user
    
        user.is_active = True
        user.is_verified = True
        user.verified_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)

        return user
    
    async def check_active_user_subscription(self, user_id) -> int | None:
        """" check active user subscription and the plan storage limits. Returns None if no active subscription, or the storage limit in MB if active subscription exists."""
        stmt = select(Subscription).where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            logger.info(f"No active subscription found for user_id: {user_id}")
            return None
        
        if subscription.end_date < datetime.now(timezone.utc):
            logger.info(f"Subscription for user_id: {user_id} has expired.")
            # Subscription has expired
            return None
        plan = await self.db.execute(select(Plan).where(Plan.plan_id == subscription.plan_id))
        plan = plan.scalar_one_or_none()
        if not plan:
            logger.warning(f"Plan with id {subscription.plan_id} not found for subscription {subscription.subscription_id}")
            return None
        storage_limit_mb = plan.storage_limit_mb
        logger.info(f"Active subscription found for user_id: {user_id} with storage limit: {storage_limit_mb} MB")
        return storage_limit_mb, plan.name

    async def save_default_subscription(self, user_id):

        stmt = select(UserModel).where(UserModel.user_id == user_id)
        plan = await self.db.execute(select(Plan).where(Plan.is_default == True))

        plan = plan.scalar_one_or_none()
        if not plan:
            return None
        
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
    
        try:
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=self.trail_period_days)
            user_subscription = Subscription(
                user_id=user.user_id,
                plan_id=plan.plan_id,
                start_date=start_date,
                end_date=end_date
            )
            self.db.add(user_subscription)
            await self.db.commit()
            await self.db.refresh(user_subscription)

            return user_subscription
        
        except Exception as e:
            await self.db.rollback()
            raise e

    async def set_password(self, user: UserModel, new_hashed_password: bytes):
        try:
            user.password = new_hashed_password
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e



def user_service(db: AsyncSession = Depends(get_db)):
    return UserService(db=db)