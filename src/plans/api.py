from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import PlanResponseSchema, PurchasePlanRequest
from src.config.database import get_db
from src.models.users.auth import UserModel
from src.services.helpers.dependencies import get_current_user
from src.models.plans.plans import Status
from .services import (
    plans, get_plan_or_none, verify_transfer,
    initialize_transfer, initialize_payment,
    get_payment, mark_payment_failed, mark_payment_successful,
    update_user_subscripton
)
from typing import List
import uuid

router = APIRouter(tags=['plans'],prefix="/plans")

@router.get("", response_model=List[PlanResponseSchema], status_code=200)
async def fetch_plans(
    request: Request, db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user)
    ):
    result = await plans(db)
    return result

@router.post("/{plan_id}/purchase", status_code=200)
async def purchase_plan(
    request: PurchasePlanRequest, user: UserModel = Depends(get_current_user),
    db: AsyncSession =  Depends(get_db), plan_id: uuid.UUID = None
): 
    plan = await get_plan_or_none(plan_id, db)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan matching request")
    if request.amount != plan.price:
        raise HTTPException(status_code=400, detail='Invalid Price')

    try:
        result = await initialize_transfer(user, request.amount)
        data = result.json()
        if not data['status']:
            raise HTTPException(status_code=502, detail=data['message'])
        
        reference = data['data']['reference']
        if reference is None:
            raise HTTPException(status_code=500, detail='Invalid reference code')
        payment = await initialize_payment(user, reference, request.amount, plan, db)
        return data
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get('/purchase/{reference}', status_code=200, response_model=PlanResponseSchema)
async def verify_plan_purchase(
    reference: str, request: Request, user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await verify_transfer(reference)
    data = result.json()
    if not data['status']:
        raise HTTPException(status=502, detail=data['message'])
    
    payment = await get_payment(reference, db)
    if payment is None:
        raise HTTPException(status_code=404, detail='payment not found')
    if payment.status != Status.Pending:
        raise HTTPException(status_code=400, detail=f"Payment already {payment.status} and closed")

    try:
        if data['data']['status'] not in ['success', 'completed', 'complete']:
            await mark_payment_failed(payment, db)
            raise HTTPException(status_code=502, detail=f'Payment failed with status: {data['data']['status']}')
        
        paid_at = data['data']['paidAt']
        await mark_payment_successful(payment, db, paid_at)
        plan = await get_plan_or_none(payment.plan_id, db)
        user_subscription = await update_user_subscripton(user, db, plan)
        await db.commit()
        return plan
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))