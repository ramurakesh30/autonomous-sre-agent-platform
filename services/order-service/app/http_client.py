
import httpx

from app import config


def create_http_client() -> httpx.AsyncClient:

    limits = httpx.Limits(
        max_connections=config.MAX_CONNECTIONS,
        max_keepalive_connections=config.MAX_KEEPALIVE_CONNECTIONS,
    )

    timeout = httpx.Timeout(
        connect=config.HTTP_CONNECT_TIMEOUT,
        read=config.HTTP_READ_TIMEOUT,
        write=config.HTTP_WRITE_TIMEOUT,
        pool=config.HTTP_POOL_TIMEOUT,
    )

    return httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    )
