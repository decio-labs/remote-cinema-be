from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import Depends

from src.models.users.auth import UserModel
from src.models.plans.plans import Plan, Subscription
from src.config.settings import setting

from datetime import datetime, timedelta
from src.config.database import get_db

class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.trail_period_days = setting.TRIAL_PERIOD_DAYS

    async def get_user_by_email(self, email: str):
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id):
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, email: str, hashed_password: bytes):
        new_user = UserModel(email=email, password=hashed_password)
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
        user.verified_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(user)

        return user
    
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
            start_date = datetime.now()
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