"""Responsible Gaming & KYC domain exceptions.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.exceptions import AppException


class ResponsibleGamingException(AppException, HTTPException):
    """Base exception for responsible gaming domain errors."""

    def __init__(
        self,
        message: str = "A responsible gaming domain error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        AppException.__init__(self, message=message, status_code=status_code, details=details)
        HTTPException.__init__(self, status_code=status_code, detail=message)


class PlayerSelfExcludedException(ResponsibleGamingException):
    """Raised when an active self-exclusion blocks gameplay or session opening (HTTP 403)."""

    def __init__(
        self,
        message: str | None = None,
        expires_at: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        formatted_date = expires_at.isoformat() if expires_at else "configured end date"
        default_message = f"Player is self-excluded until {formatted_date}. Access denied."
        msg = message or default_message
        payload = details or {"error": "player_self_excluded"}
        if expires_at:
            payload["expires_at"] = expires_at.isoformat()
        super().__init__(
            message=msg,
            status_code=status.HTTP_403_FORBIDDEN,
            details=payload,
        )


class DailyBetLimitExceededException(ResponsibleGamingException):
    """Raised when an attempted bet exceeds the player's 24-hour bet volume limit (HTTP 409)."""

    def __init__(
        self,
        message: str | None = None,
        limit: int | None = None,
        current: int | None = None,
        attempted: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        default_message = (
            f"Daily bet limit of {limit} exceeded. Current 24h bet volume: {current}, attempted bet: {attempted}."
        )
        msg = message or default_message
        payload = details or {
            "error": "daily_bet_limit_exceeded",
            "limit": limit,
            "current": current,
            "attempted": attempted,
        }
        super().__init__(
            message=msg,
            status_code=status.HTTP_409_CONFLICT,
            details=payload,
        )


class SessionDurationExceededException(ResponsibleGamingException):
    """Raised when a player's game session exceeds the configured maximum duration (HTTP 409)."""

    def __init__(
        self,
        message: str | None = None,
        max_duration_minutes: int | None = None,
        elapsed_minutes: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        default_message = (
            f"Session duration limit of {max_duration_minutes} minutes exceeded. Elapsed: {elapsed_minutes} minutes."
        )
        msg = message or default_message
        payload = details or {
            "error": "session_duration_exceeded",
            "max_duration_minutes": max_duration_minutes,
            "elapsed_minutes": elapsed_minutes,
        }
        super().__init__(
            message=msg,
            status_code=status.HTTP_409_CONFLICT,
            details=payload,
        )


class KycProfileNotFoundException(ResponsibleGamingException):
    """Raised when a requested KYC profile is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "KYC profile not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"error": "kyc_profile_not_found"},
        )


class InvalidKycTransitionException(ResponsibleGamingException):
    """Raised when an invalid KYC status transition is requested (HTTP 400)."""

    def __init__(
        self,
        message: str = "Invalid KYC status transition",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "invalid_kyc_transition"},
        )
