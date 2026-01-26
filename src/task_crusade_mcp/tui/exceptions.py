"""TUI exception classes for error handling with toast notifications.

This module defines exception classes used by the TUI data service layer.
When the TUIDataService encounters errors fetching or updating data, it raises
these exceptions, and widgets catch them to display toast notifications to users.

Example usage:
    try:
        campaigns = await self.data_service.get_campaigns()
    except DataFetchError as e:
        self.notify(str(e), severity="error")
        campaigns = []
"""


class TUIError(Exception):
    """Base exception for TUI errors."""


class DataFetchError(TUIError):
    """Raised when data cannot be fetched from services.

    Attributes:
        operation: The operation that failed (e.g., "fetch campaigns", "load tasks")
        message: Detailed error message describing the failure

    Example:
        >>> raise DataFetchError("fetch campaigns", "Database connection failed")
        >>> # str(error) -> "Failed to fetch campaigns: Database connection failed"
    """

    def __init__(self, operation: str, message: str):
        """Initialize DataFetchError.

        Args:
            operation: The operation that failed
            message: Detailed error message
        """
        self.operation = operation
        self.message = message
        super().__init__(f"Failed to {operation}: {message}")


class DataUpdateError(TUIError):
    """Raised when data cannot be updated.

    Attributes:
        operation: The operation that failed (e.g., "update status", "mark complete")
        entity_id: The ID of the entity that could not be updated
        message: Detailed error message describing the failure

    Example:
        >>> raise DataUpdateError("update status", "task-123", "Task not found")
        >>> # str(error) -> "Failed to update status task-123: Task not found"
    """

    def __init__(self, operation: str, entity_id: str, message: str):
        """Initialize DataUpdateError.

        Args:
            operation: The operation that failed
            entity_id: The ID of the entity that could not be updated
            message: Detailed error message
        """
        self.operation = operation
        self.entity_id = entity_id
        self.message = message
        super().__init__(f"Failed to {operation} {entity_id}: {message}")
