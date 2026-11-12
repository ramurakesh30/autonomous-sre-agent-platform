
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request

from app import config
from app.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)
from app.http_client import create_http_client
from app.resilience import call_payment_with_retry
from app.schemas import OrderRequest, OrderResponse


@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.http_client = create_http_client()

    app.state.payment_breaker = CircuitBreaker(
        failure_threshold=config.CIRCUIT_FAILURE_THRESHOLD,
        recovery_timeout=config.CIRCUIT_RECOVERY_TIMEOUT,
    )

    yield

    await app.state.http_client.aclose()


app = FastAPI(
    title="Order Service",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post(
    "/orders",
    response_model=OrderResponse,
)
async def create_order(
    order: OrderRequest,
    request: Request,
):

    order_id = str(uuid4())

    payload = {
        "order_id": order_id,
        "amount": str(order.amount),
        "currency": order.currency,
    }

    client = request.app.state.http_client
    breaker = request.app.state.payment_breaker

    async def process_payment():

        return await call_payment_with_retry(
            client=client,
            url=f"{config.PAYMENT_SERVICE_URL}/payments",
            payload=payload,
            idempotency_key=f"{order_id}-payment",
        )

    try:

        payment_result = await breaker.call(
            process_payment
        )

    except CircuitOpenError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
            headers={"Retry-After": "10"},
        )

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="Payment service timed out",
        )

    except httpx.RequestError:

        raise HTTPException(
            status_code=503,
            detail="Payment service unavailable",
        )

    except httpx.HTTPStatusError as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Payment service error: {exc.response.status_code}",
        )

    return OrderResponse(
        order_id=order_id,
        payment_id=payment_result["payment_id"],
        status=payment_result["status"],
    )
