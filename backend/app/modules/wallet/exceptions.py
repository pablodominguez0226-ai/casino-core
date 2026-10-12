from typing import Any

from fastapi import HTTPException, status

from app.core.exceptions import AppException


class WalletException(AppException, HTTPException):
    """Base domain exception for wallet and ledger operations."""

    def __init__(
        self,
        message: str = "A wallet domain error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        AppException.__init__(self, message=message, status_code=status_code, details=details)
        HTTPException.__init__(self, status_code=status_code, detail=message)


class InsufficientFundsException(WalletException):
    """Raised when the wallet balance is less than the requested transaction amount (HTTP 409)."""

    def __init__(
        self,
        message: str = "Insufficient funds in wallet for requested transaction",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details or {"error": "insufficient_funds"},
        )


class WalletLockedException(WalletException):
    """Raised when an operation is attempted on a locked or disabled wallet (HTTP 423)."""

    def __init__(
        self,
        message: str = "Wallet is locked and cannot perform financial operations",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_423_LOCKED,
            details=details or {"error": "wallet_locked"},
        )


class DuplicateTransactionException(WalletException):
    """Raised when an idempotency key collides with a different payload or cannot be reused (HTTP 400)."""

    def __init__(
        self,
        message: str = "Idempotency key already processed with different payload",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {"error": "duplicate_transaction_conflict"},
        )


class WalletNotFoundException(WalletException):
    """Raised when the requested wallet entity is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Wallet not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"error": "wallet_not_found"},
        )
