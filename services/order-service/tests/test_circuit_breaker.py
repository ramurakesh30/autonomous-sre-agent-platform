
import asyncio

import httpx
import pytest

from app.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold():

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10,
    )

    async def failing_operation():
        raise httpx.ConnectError("Connection refused")

    for _ in range(2):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(failing_operation)

    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError):
        await breaker.call(failing_operation)


@pytest.mark.asyncio
async def test_circuit_recovers():

    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0.05,
    )

    async def failing_operation():
        raise httpx.ConnectError("Connection refused")

    with pytest.raises(httpx.ConnectError):
        await breaker.call(failing_operation)

    await asyncio.sleep(0.06)

    async def successful_operation():
        return "SUCCESS"

    result = await breaker.call(successful_operation)

    assert result == "SUCCESS"
    assert breaker.state == CircuitState.CLOSED
