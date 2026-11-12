
import json
import logging
import sys

from datetime import datetime, timezone
from opentelemetry import trace
from pathlib import Path


class JsonFormatter(logging.Formatter):

    def format(self, record):

        span_context = (
            trace.get_current_span().get_span_context()
        )

        trace_id = None
        span_id = None

        if span_context.is_valid:
            trace_id = format(
                span_context.trace_id, "032x"
            )
            span_id = format(
                span_context.span_id, "016x"
            )

        log_data = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": "order-service",
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data)


def configure_logging():

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_dir / "order-service.jsonl",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger("order-service")
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    return logger
