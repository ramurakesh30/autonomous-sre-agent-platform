
import os


PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL",
    "http://localhost:8001",
)

HTTP_CONNECT_TIMEOUT = float(
    os.getenv("HTTP_CONNECT_TIMEOUT", "1.0")
)

HTTP_READ_TIMEOUT = float(
    os.getenv("HTTP_READ_TIMEOUT", "2.0")
)

HTTP_WRITE_TIMEOUT = float(
    os.getenv("HTTP_WRITE_TIMEOUT", "2.0")
)

HTTP_POOL_TIMEOUT = float(
    os.getenv("HTTP_POOL_TIMEOUT", "1.0")
)

MAX_CONNECTIONS = int(
    os.getenv("MAX_CONNECTIONS", "100")
)

MAX_KEEPALIVE_CONNECTIONS = int(
    os.getenv("MAX_KEEPALIVE_CONNECTIONS", "20")
)

MAX_RETRY_ATTEMPTS = int(
    os.getenv("MAX_RETRY_ATTEMPTS", "3")
)

BASE_RETRY_DELAY = float(
    os.getenv("BASE_RETRY_DELAY", "0.5")
)

MAX_RETRY_DELAY = float(
    os.getenv("MAX_RETRY_DELAY", "3.0")
)

CIRCUIT_FAILURE_THRESHOLD = int(
    os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3")
)

CIRCUIT_RECOVERY_TIMEOUT = float(
    os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "10.0")
)
