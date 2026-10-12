import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User


class SystemMetrics(BaseModel):
    """Schema representing platform telemetry and operational health metrics."""

    total_requests: int = Field(..., description="Total HTTP requests processed")
    requests_by_status: dict[str, int] = Field(
        ..., description="Requests grouped by HTTP status class (2xx, 3xx, 4xx, 5xx)"
    )
    requests_by_status_code: dict[str, int] = Field(
        ..., description="Detailed request counts per exact status code"
    )
    average_latency_ms: float = Field(..., description="Average request latency in milliseconds")
    total_financial_transactions: int = Field(
        ..., description="Total financial ledger transactions processed"
    )
    uptime_seconds: float = Field(..., description="Platform uptime in seconds")


class MetricsCollector:
    """Thread-safe in-memory telemetry metrics counter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_requests: int = 0
        self._total_latency_ms: float = 0.0
        self._status_classes: dict[str, int] = {
            "2xx": 0,
            "3xx": 0,
            "4xx": 0,
            "5xx": 0,
        }
        self._status_codes: dict[str, int] = {}
        self._total_financial_transactions: int = 0

    def record_request(self, status_code: int, latency_ms: float) -> None:
        """Record an incoming request status code and latency measurement."""
        with self._lock:
            self._total_requests += 1
            self._total_latency_ms += latency_ms

            status_class = f"{status_code // 100}xx"
            if status_class in self._status_classes:
                self._status_classes[status_class] += 1
            else:
                self._status_classes[status_class] = 1

            code_str = str(status_code)
            self._status_codes[code_str] = self._status_codes.get(code_str, 0) + 1

    def record_financial_transaction(self, count: int = 1) -> None:
        """Increment count of processed ledger financial operations."""
        with self._lock:
            self._total_financial_transactions += count

    def get_metrics(self) -> dict[str, Any]:
        """Snapshot current operational telemetry metrics."""
        with self._lock:
            avg_latency = (
                round(self._total_latency_ms / self._total_requests, 2)
                if self._total_requests > 0
                else 0.0
            )
            return {
                "total_requests": self._total_requests,
                "requests_by_status": dict(self._status_classes),
                "requests_by_status_code": dict(self._status_codes),
                "average_latency_ms": avg_latency,
                "total_financial_transactions": self._total_financial_transactions,
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    def reset(self) -> None:
        """Reset metrics counters (useful for unit tests isolation)."""
        with self._lock:
            self._start_time = time.time()
            self._total_requests = 0
            self._total_latency_ms = 0.0
            self._status_classes = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
            self._status_codes = {}
            self._total_financial_transactions = 0


# Global singleton instance
metrics_collector = MetricsCollector()


def verify_admin_or_monitor(current_user: User = Depends(get_current_user)) -> User:
    """Ensure that the authenticated actor holds administrative or auditor privileges."""
    user_roles = {r.name for r in current_user.roles}
    user_perms = {p.code for r in current_user.roles for p in r.permissions}

    allowed_roles = {"SUPER_ADMIN", "OPERATOR_ADMIN", "COMPLIANCE"}
    allowed_perms = {"system:admin", "operator:admin", "reports:read", "audit:read"}

    if not (user_roles & allowed_roles or user_perms & allowed_perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin or monitor privilege required",
        )
    return current_user


router = APIRouter(prefix="/metrics", tags=["telemetry"])


@router.get(
    "",
    response_model=SystemMetrics,
    summary="Retrieve system telemetry and operational metrics",
    description="Returns HTTP traffic stats, latency averages, and financial ledger transaction counts.",
)
async def get_metrics(
    _: User = Depends(verify_admin_or_monitor),
) -> SystemMetrics:
    """Retrieve system telemetry metrics for administrators and monitors."""
    data = metrics_collector.get_metrics()
    return SystemMetrics(**data)
