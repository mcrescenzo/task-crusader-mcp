"""
Domain Result Types - Pure Business Logic Results.

These types represent the outcome of domain operations without any
infrastructure or presentation concerns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar


class DomainErrorType(Enum):
    """Types of domain errors."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    DEPENDENCY_ERROR = "dependency_error"
    OPERATION_FAILED = "operation_failed"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"


T = TypeVar("T")


@dataclass
class DomainResult(Generic[T]):
    """
    Base result type for domain operations.

    Represents either success with data or failure with error information.
    This is a pure domain type with no infrastructure dependencies.
    """

    success: bool
    data: Optional[T] = None
    error_type: Optional[DomainErrorType] = None
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.success

    @property
    def is_failure(self) -> bool:
        """Check if result is a failure."""
        return not self.success

    def get_data_or_raise(self) -> T:
        """Get data or raise exception if failed."""
        if self.is_failure:
            raise ValueError(f"Cannot get data from failed result: {self.error_message}")
        return self.data  # type: ignore

    def get_data_or_default(self, default: T) -> T:
        """Get data or return default if failed."""
        return self.data if self.is_success and self.data is not None else default


@dataclass
class DomainSuccess(Generic[T]):
    """
    Factory for creating successful domain results.

    Usage:
        result = DomainSuccess.create(data=task)
    """

    @staticmethod
    def create(
        data: Optional[T] = None, suggestions: Optional[List[str]] = None
    ) -> DomainResult[T]:
        """Create a successful domain result."""
        return DomainResult(success=True, data=data, suggestions=suggestions or [])


@dataclass
class DomainError:
    """
    Factory for creating failed domain results.

    Usage:
        result = DomainError.validation_error("Invalid input", details={"field": "name"})
    """

    @staticmethod
    def create(
        error_type: DomainErrorType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> DomainResult[Any]:
        """Create a failed domain result."""
        return DomainResult(
            success=False,
            error_type=error_type,
            error_message=message,
            error_details=details or {},
            suggestions=suggestions or [],
        )

    @staticmethod
    def validation_error(
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> DomainResult[Any]:
        """Create a validation error result."""
        return DomainError.create(
            DomainErrorType.VALIDATION_ERROR,
            message,
            details,
            suggestions or ["Check input format and try again"],
        )

    @staticmethod
    def not_found(
        resource: str, resource_id: str, suggestions: Optional[List[str]] = None
    ) -> DomainResult[Any]:
        """Create a not found error result."""
        return DomainError.create(
            DomainErrorType.NOT_FOUND,
            f"{resource} '{resource_id}' not found",
            {"resource": resource, "id": resource_id},
            suggestions or [f"Verify the {resource.lower()} ID and try again"],
        )

    @staticmethod
    def already_exists(
        resource: str, identifier: str, suggestions: Optional[List[str]] = None
    ) -> DomainResult[Any]:
        """Create an already exists error result."""
        return DomainError.create(
            DomainErrorType.ALREADY_EXISTS,
            f"{resource} '{identifier}' already exists",
            {"resource": resource, "identifier": identifier},
            suggestions or [f"Use a different {resource.lower()} identifier"],
        )

    @staticmethod
    def business_rule_violation(
        rule: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> DomainResult[Any]:
        """Create a business rule violation error result."""
        return DomainError.create(
            DomainErrorType.BUSINESS_RULE_VIOLATION,
            message,
            {**(details or {}), "rule": rule},
            suggestions,
        )

    @staticmethod
    def dependency_error(
        dependency: str, message: str, suggestions: Optional[List[str]] = None
    ) -> DomainResult[Any]:
        """Create a dependency error result."""
        return DomainError.create(
            DomainErrorType.DEPENDENCY_ERROR,
            message,
            {"dependency": dependency},
            suggestions or [f"Ensure {dependency} is available and properly configured"],
        )

    @staticmethod
    def operation_failed(
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> DomainResult[Any]:
        """Create an operation failed error result."""
        return DomainError.create(
            DomainErrorType.OPERATION_FAILED,
            f"Operation '{operation}' failed: {reason}",
            {**(details or {}), "operation": operation},
            suggestions,
        )

    @staticmethod
    def unauthorized(
        message: str = "Unauthorized access", suggestions: Optional[List[str]] = None
    ) -> DomainResult[Any]:
        """Create an unauthorized error result."""
        return DomainError.create(
            DomainErrorType.UNAUTHORIZED,
            message,
            {},
            suggestions or ["Check authentication credentials"],
        )

    @staticmethod
    def forbidden(
        resource: str, action: str, suggestions: Optional[List[str]] = None
    ) -> DomainResult[Any]:
        """Create a forbidden error result."""
        return DomainError.create(
            DomainErrorType.FORBIDDEN,
            f"Access forbidden: Cannot {action} {resource}",
            {"resource": resource, "action": action},
            suggestions or ["Check user permissions"],
        )
