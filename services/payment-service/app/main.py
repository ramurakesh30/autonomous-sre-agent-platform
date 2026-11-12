
import asyncio
import os
from uuid import uuid4

from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from app.logging_config import configure_logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.tracing import (
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)

from app.schemas import PaymentRequest, PaymentResponse

logger = configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        shutdown_tracing()


app = FastAPI(lifespan=lifespan)

setup_tracing(app, "payment-service")

tracer = get_tracer(__name__)

# Educational in-memory storage.
# This will later be replaced by PostgreSQL.
payments_by_key: dict[str, PaymentResponse] = {}
requests_by_key: dict[str, PaymentRequest] = {}

payment_lock = asyncio.Lock()


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    
    #if os.getenv("SIMULATE_PAYMENT_FAILURE", "true").lower() == "true":
    #    logger.error("Simulated payment provider outage")
    #
    #    raise HTTPException(
    #        status_code=503,
    #        detail="Simulated payment provider unavailable",
    #    )

    #logger.info("Payment processing started")
    with tracer.start_as_current_span("payment_processing") as span:
        span.set_attribute("payment.currency", payment.currency.upper())
        span.set_attribute("order.id", payment.order_id)

        async with payment_lock:
            previous = requests_by_key.get(idempotency_key)
            if previous is not None:
                if previous != payment:
                    raise HTTPException(409, "Idempotency key reused with different request")
                return payments_by_key[idempotency_key]

        delay = float(os.getenv("PAYMENT_SIMULATED_DELAY", "0"))
        if delay:
            await asyncio.sleep(delay)
        if os.getenv("PAYMENT_SIMULATED_FAILURE", "false").lower() == "true":
            span.set_status(Status(StatusCode.ERROR, "Simulated payment failure"))
            raise HTTPException(503, "Simulated payment failure")

        async with payment_lock:
            previous = requests_by_key.get(idempotency_key)
            if previous is not None:
                if previous != payment:
                    raise HTTPException(409, "Idempotency key reused with different request")
                return payments_by_key[idempotency_key]
            result = PaymentResponse(
                payment_id=str(uuid4()),
                order_id=payment.order_id,
                amount=payment.amount,
                currency=payment.currency.upper(),
                status="succeeded",
            )
            requests_by_key[idempotency_key] = payment
            payments_by_key[idempotency_key] = result
            logger.info("Payment successfully created")
            return result
