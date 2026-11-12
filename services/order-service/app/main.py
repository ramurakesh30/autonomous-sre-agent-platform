
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from opentelemetry.trace import Status, StatusCode

from app import config
from app.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)
from app.http_client import create_http_client
from app.logging_config import configure_logging
from app.resilience import call_payment_with_retry
from app.schemas import OrderRequest, OrderResponse
from app.tracing import get_tracer, setup_tracing, shutdown_tracing

logger = configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.http_client = create_http_client()

    app.state.payment_breaker = CircuitBreaker(
        failure_threshold=config.CIRCUIT_FAILURE_THRESHOLD,
        recovery_timeout=config.CIRCUIT_RECOVERY_TIMEOUT,
    )

    try:
        yield
    finally:
        await app.state.http_client.aclose()
        shutdown_tracing()


app = FastAPI(
    title="Order Service",
    lifespan=lifespan,
)

setup_tracing(app, "order-service")

tracer = get_tracer(__name__)

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post(
    "/orders",
    response_model=OrderResponse,
)
async def create_order(
    order: OrderRequest):

    logger.info("Order processing started")
    order_id = str(uuid4())
    payment_payload = {
        "order_id": order_id,
        "amount": str(order.amount),
        "currency": order.currency.upper(),
    }
    try:
        with tracer.start_as_current_span("process_payment") as span:
            span.set_attribute("order.id", order_id)
            span.set_attribute("payment.currency", order.currency.upper())
            try:
                payment = await app.state.payment_breaker.call(
                    lambda: call_payment_with_retry(
                        client=app.state.http_client,
                        url=f"{config.PAYMENT_SERVICE_URL}/payments",
                        payload=payment_payload,
                        idempotency_key=order_id,
                    )
                )
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            logger.info("Payment processing completed")
            
        return OrderResponse(order_id=order_id, status="created", payment=payment)
    except CircuitOpenError as exc:
        raise HTTPException(
            status_code=503,
            detail="Payment service temporarily unavailable (circuit open)",
            headers={"Retry-After": str(int(config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT))},
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Payment service timed out") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Payment service unavailable") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Payment service returned HTTP {exc.response.status_code}",
        ) from exc
