import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.telemetry.logging import request_id_ctx
from app.core.telemetry.metrics import metrics_collector

logger = logging.getLogger("app.telemetry")


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware capturing request correlation ID, tracking request latency, and structured logging."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Capture incoming X-Request-ID or generate new UUIDv4
        incoming_request_id = request.headers.get("X-Request-ID")
        if incoming_request_id and incoming_request_id.strip():
            request_id = incoming_request_id.strip()
        else:
            request_id = str(uuid.uuid4())

        # 2. Set correlation ID in ambient contextvar and request state
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        # 3. Track request latency and client IP
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Record telemetry metrics
            metrics_collector.record_request(
                status_code=response.status_code,
                latency_ms=latency_ms,
            )

            # Log structured access event with correlation attributes
            logger.info(
                "HTTP %s %s completed with status %d in %.2fms",
                request.method,
                request.url.path,
                response.status_code,
                latency_ms,
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
            )

            # Inject X-Request-ID into response header
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics_collector.record_request(
                status_code=500,
                latency_ms=latency_ms,
            )

            logger.error(
                "HTTP %s %s unhandled exception after %.2fms: %s",
                request.method,
                request.url.path,
                latency_ms,
                exc,
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": latency_ms,
                },
            )
            raise
        finally:
            request_id_ctx.reset(token)
