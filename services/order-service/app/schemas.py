
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = "EUR"


class OrderResponse(BaseModel):
    order_id: str
    payment_id: str
    status: str
