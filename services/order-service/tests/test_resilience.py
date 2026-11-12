
import httpx
import pytest

from app.resilience import call_payment_with_retry


@pytest.mark.asyncio
async def test_retry_succeeds_after_503():

    attempts = 0

    async def handler(request):

        nonlocal attempts
        attempts += 1

        if attempts == 1:
            return httpx.Response(503)

        return httpx.Response(
            200,
            json={
                "payment_id": "PAY-001",
                "order_id": "ORD-001",
                "status": "AUTHORIZED",
                "amount": "100.00",
                "currency": "EUR",
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        result = await call_payment_with_retry(
            client=client,
            url="http://payment/payments",
            payload={
                "order_id": "ORD-001",
                "amount": "100.00",
                "currency": "EUR",
            },
            idempotency_key="ORD-001-payment",
        )

    assert result["payment_id"] == "PAY-001"
    assert attempts == 2


@pytest.mark.asyncio
async def test_http_400_is_not_retried():

    attempts = 0

    async def handler(request):

        nonlocal attempts
        attempts += 1

        return httpx.Response(
            400,
            json={"detail": "Invalid request"},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        with pytest.raises(httpx.HTTPStatusError):

            await call_payment_with_retry(
                client=client,
                url="http://payment/payments",
                payload={
                    "order_id": "ORD-001",
                    "amount": "100.00",
                    "currency": "EUR",
                },
                idempotency_key="ORD-001-payment",
            )

    assert attempts == 1
