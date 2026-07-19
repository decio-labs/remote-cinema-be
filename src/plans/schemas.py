from pydantic import BaseModel
import uuid
import decimal
from datetime import datetime

class PlanResponseSchema(BaseModel):
    plan_id: uuid.UUID
    name: str  = None
    description: str | None = None
    price: decimal.Decimal | None = None
    storage_limit_mb: int = 0
    is_default: bool = False
    created_at: datetime
    is_daily: bool | None = False
    is_monthly: bool | None = False

class PurchasePlanRequest(BaseModel):
    amount: decimal.Decimal
