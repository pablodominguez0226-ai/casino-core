import contextvars
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any

# Context variable preserving Correlation ID across asynchronous request contexts
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability.

    Formats log records into JSON objects containing timestamp, level, message,
    correlation ID (request_id), module name, and optional exception tracebacks.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Resolve request_id from log record attribute or ambient ContextVar
        request_id = getattr(record, "request_id", None) or request_id_ctx.get(None)

        exception_str: str | None = None
        if record.exc_info:
            exception_str = self.formatException(record.exc_info)

        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id,
            "module": record.name,
            "exception": exception_str,
        }

        # Include custom extra fields if provided
        standard_attrs = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "request_id",
        }
        for key, val in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_payload[key] = val

        return json.dumps(log_payload, default=str)


def setup_telemetry_logging(log_level: str = "INFO") -> None:
    """Configure root and framework loggers to output structured JSON to stdout."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clear pre-existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(numeric_level)
    root_logger.addHandler(json_handler)

    # Configure Uvicorn loggers to use JSON format
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = [json_handler]
        uv_logger.propagate = False
