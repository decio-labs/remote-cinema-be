from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.plans.plans import Plan, Subscription, SubscriptionStatus
from src.models.users.auth import UserModel
from src.config.settings import get_settings
from src.models.plans.plans import Payment, Status

from datetime import datetime, timedelta
import requests
import uuid
import decimal
setting = get_settings()

class DuplicateTransaction(Exception):
    pass

def _headers():
    return {"Authorization": f"Bearer {setting.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}

async def plans(db: AsyncSession):
    stmt = select(Plan)
    plans = await db.execute(stmt)
    result = plans.scalars().all()
    return result

async def get_plan_or_none(plan_id: uuid.UUID, db: AsyncSession) -> Plan | None:
    stmt = select(Plan).where(Plan.plan_id == plan_id)
    plan = await db.execute(stmt)
    return plan.scalar_one_or_none()


async def initialize_transfer(user: UserModel, amount: decimal.Decimal):
    reference = f'txn-utx-{uuid.uuid4()}'
    url = f"{setting.PAYSTACK_BASE_URL}/transaction/initialize"
    payload = {
        "email": user.email,
        "amount": float(amount) * 100,
        "channels": ["card", "bank", "apple_pay", "ussd", "bank_transfer"],
        "currency": "NGN",
        "reference": reference
    }
    response = requests.post(url, json=payload, headers=_headers())
    return response


async def verify_transfer(reference: str):
    url = f"{setting.PAYSTACK_BASE_URL}/transaction/verify/{reference}"
    response = requests.get(url, headers=_headers())
    return response

async def initialize_payment(user: UserModel, reference: str, amount: decimal.Decimal, plan: Plan, db: AsyncSession):
    stmt = select(Payment).where(Payment.reference == reference)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise DuplicateTransaction("Duplicate Transaction Found")
    
    payment = Payment(
        user_id=user.user_id, plan_id=plan.plan_id, 
        amount=amount, reference=reference)
    
    db.add(payment)
    await db.commit()
    await db.flush()
    await db.refresh(payment)
    return payment

async def get_payment(reference: str, db: AsyncSession):
    stmt = select(Payment).where(Payment.reference == reference)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def mark_payment_successful(payment: Payment, db: AsyncSession, paid_at: datetime):
    return await db.execute(
        update(Payment).where(Payment.reference == payment.reference
                      ).values(status=Status.Success, paid_at=datetime.fromisoformat(paid_at)))

async def mark_payment_failed(payment: Payment, db: AsyncSession):
    return await db.execute(
        update(Payment).where(Payment.reference == payment.reference
                              ).values(status=Status.Failed)
    )

async def update_user_subscripton(user: UserModel, db: AsyncSession, plan: Plan):
    end_date = None
    start_date = datetime.now()

    if plan.is_daily:
        end_date = start_date + timedelta(hours=24)
    if plan.is_monthly:
        end_date = start_date + timedelta(days=30)
    
    stmt = (
        update(Subscription).where(
            Subscription.user_id == user.user_id
            ).values(
                plan_id=plan.plan_id, start_date=start_date, end_date=end_date, 
                status=SubscriptionStatus.ACTIVE
            )
        )

    result = await db.execute(stmt)
    return True
