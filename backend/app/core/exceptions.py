from typing import Any


class AppException(Exception):
    """Base exception for all domain and application errors."""

    def __init__(
        self,
        message: str = "An unexpected application error occurred",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.status_code: int = status_code
        self.details: dict[str, Any] = details or {}


class DatabaseConnectionError(AppException):
    """Raised when the database connection fails or times out."""

    def __init__(
        self,
        message: str = "Unable to connect to the database",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=503, details=details)


class EntityNotFoundError(AppException):
    """Raised when a requested domain entity is not found."""

    def __init__(
        self,
        entity_name: str,
        identifier: Any,
    ) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found",
            status_code=404,
            details={"entity_name": entity_name, "identifier": str(identifier)},
        )


class EntityAlreadyExistsError(AppException):
    """Raised when an entity with a duplicate unique constraint is created."""

    def __init__(
        self,
        entity_name: str,
        conflict_field: str,
        value: Any,
    ) -> None:
        super().__init__(
            message=f"{entity_name} with {conflict_field} '{value}' already exists",
            status_code=409,
            details={"entity_name": entity_name, "field": conflict_field, "value": str(value)},
        )
