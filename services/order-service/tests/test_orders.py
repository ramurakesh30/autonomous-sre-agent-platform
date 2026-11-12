
import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_order_when_payment_service_unavailable():

    # Simulate the Payment Service being unavailable.
    async def payment_handler(request):
        raise httpx.ConnectError(
            "Payment service unavailable",
            request=request,
        )

    mock_transport = httpx.MockTransport(payment_handler)

    # Run the FastAPI application's lifespan so that
    # its shared HTTP client and circuit breaker are initialized.
    async with app.router.lifespan_context(app):

        original_client = app.state.http_client

        # This client is used internally by the Order Service
        # when it calls the Payment Service.
        payment_mock_client = httpx.AsyncClient(
            transport=mock_transport
        )

        app.state.http_client = payment_mock_client

        try:
            # This client sends requests TO the FastAPI application.
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as test_client:

                response = await test_client.post(
                    "/orders",
                    json={
                        "amount": "100.00",
                        "currency": "EUR",
                    },
                )

            assert response.status_code == 503

        finally:
            # Restore the original application client.
            app.state.http_client = original_client
            await payment_mock_client.aclose()
