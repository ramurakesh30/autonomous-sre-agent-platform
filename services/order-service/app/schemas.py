
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = "EUR"

class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    status: str
    amount: Decimal
    currency: str

class OrderResponse(BaseModel):
    order_id: str
    status: str
    payment: PaymentResponse
