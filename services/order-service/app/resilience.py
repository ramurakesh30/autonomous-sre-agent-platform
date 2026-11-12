
import asyncio
import random

import httpx

from app import config


RETRYABLE_STATUS_CODES = {
    502,
    503,
    504,
}


async def call_payment_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    idempotency_key: str,
):

    for attempt in range(config.MAX_RETRY_ATTEMPTS):

        try:

            response = await client.post(
                url,
                json=payload,
                headers={
                    "Idempotency-Key": idempotency_key
                },
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                response.raise_for_status()

            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as exc:

            if (
                exc.response.status_code
                not in RETRYABLE_STATUS_CODES
            ):
                raise

            if attempt == config.MAX_RETRY_ATTEMPTS - 1:
                raise

        except (
            httpx.TimeoutException,
            httpx.ConnectError,
        ):

            if attempt == config.MAX_RETRY_ATTEMPTS - 1:
                raise

        delay_cap = min(
            config.MAX_RETRY_DELAY,
            config.BASE_RETRY_DELAY * (2 ** attempt),
        )

        delay = random.uniform(0, delay_cap)

        await asyncio.sleep(delay)

    raise RuntimeError("Payment retries exhausted")
