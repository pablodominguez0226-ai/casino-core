"""Gaming domain exceptions.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from typing import Any

from fastapi import HTTPException, status

from app.core.exceptions import AppException


class GamingException(AppException, HTTPException):
    """Base domain exception for gaming operations."""

    def __init__(
        self,
        message: str = "A gaming domain error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        AppException.__init__(self, message=message, status_code=status_code, details=details)
        HTTPException.__init__(self, status_code=status_code, detail=message)


class GameNotFoundException(GamingException):
    """Raised when the requested game entity is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Game not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"error": "game_not_found"},
        )


class GameSessionNotFoundException(GamingException):
    """Raised when the requested game session entity is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Game session not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"error": "game_session_not_found"},
        )


class GameSessionInactiveException(GamingException):
    """Raised when attempting an action on an inactive game session (HTTP 400)."""

    def __init__(
        self,
        message: str = "Game session is not active",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "game_session_inactive"},
        )


class InvalidBetAmountException(GamingException):
    """Raised when a bet amount is outside allowed minimum or maximum limits (HTTP 422)."""

    def __init__(
        self,
        message: str = "Invalid bet amount",
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            details=details or {"error": "invalid_bet_amount"},
        )


class InvalidRouletteBetException(GamingException):
    """Raised when an individual roulette bet or composite structure is invalid (HTTP 400)."""

    def __init__(
        self,
        message: str = "Invalid roulette bet configuration",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "invalid_roulette_bet"},
        )


class GameRoundNotFoundException(GamingException):
    """Raised when the requested game round entity is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Game round not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"error": "game_round_not_found"},
        )


class InvalidBlackjackActionException(GamingException):
    """Raised when an invalid blackjack action is attempted on a round (HTTP 400)."""

    def __init__(
        self,
        message: str = "Invalid blackjack action",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "invalid_blackjack_action"},
        )


class GameRoundAlreadySettledException(GamingException):
    """Raised when attempting an action on a game round that has already been settled (HTTP 400)."""

    def __init__(
        self,
        message: str = "Game round is already settled",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "game_round_already_settled"},
        )

