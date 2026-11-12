
import asyncio
import os
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException

from app.schemas import PaymentRequest, PaymentResponse

app = FastAPI(title="Payment Service")

# Educational in-memory storage.
# This will later be replaced by PostgreSQL.
payments: dict[str, PaymentResponse] = {}
payment_requests: dict[str, PaymentRequest] = {}

payment_lock = asyncio.Lock()


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/payments", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    delay = float(os.getenv("PAYMENT_SIMULATED_DELAY", "0"))
    failure = os.getenv("PAYMENT_SIMULATED_FAILURE", "false")

    if delay > 0:
        await asyncio.sleep(delay)

    if failure.lower() == "true":
        raise HTTPException(
            status_code=503,
            detail="Simulated payment service failure",
        )

    async with payment_lock:

        if idempotency_key in payments:

            if payment_requests[idempotency_key] != request:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key reused with different payload",
                )

            return payments[idempotency_key]

        result = PaymentResponse(
            payment_id=str(uuid4()),
            order_id=request.order_id,
            status="AUTHORIZED",
            amount=request.amount,
            currency=request.currency,
        )

        payments[idempotency_key] = result
        payment_requests[idempotency_key] = request

        return result
