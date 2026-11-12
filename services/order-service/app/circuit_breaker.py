
import asyncio
import time
from enum import Enum
from typing import Callable

import httpx


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    pass


def is_dependency_failure(exc: Exception) -> bool:

    if isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
        ),
    ):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {
            500, 502, 503, 504
        }

    return False


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 10.0,
        failure_classifier: Callable[
            [Exception], bool
        ] = is_dependency_failure,
    ):

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_classifier = failure_classifier

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None

        self.probe_in_progress = False
        self.lock = asyncio.Lock()

    async def call(self, operation):

        async with self.lock:

            if self.state == CircuitState.OPEN:

                elapsed = (
                    time.monotonic() - self.opened_at
                )

                if elapsed < self.recovery_timeout:
                    raise CircuitOpenError(
                        "Payment circuit is OPEN"
                    )

                self.state = CircuitState.HALF_OPEN

            if self.state == CircuitState.HALF_OPEN:

                if self.probe_in_progress:
                    raise CircuitOpenError(
                        "Recovery probe already running"
                    )

                self.probe_in_progress = True

        try:
            result = await operation()

        except Exception as exc:

            if self.failure_classifier(exc):

                async with self.lock:

                    self.failure_count += 1

                    if (
                        self.state == CircuitState.HALF_OPEN
                        or self.failure_count >= self.failure_threshold
                    ):
                        self.state = CircuitState.OPEN
                        self.opened_at = time.monotonic()

            async with self.lock:
                self.probe_in_progress = False

            raise

        async with self.lock:

            self.failure_count = 0
            self.state = CircuitState.CLOSED
            self.opened_at = None
            self.probe_in_progress = False

        return result
