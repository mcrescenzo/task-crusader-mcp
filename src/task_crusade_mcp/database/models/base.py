"""
Database Models Base Classes and Utilities.

Shared base classes, utilities, and common functionality for all database models.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""

    pass


def generate_id() -> str:
    """Generate a unique ID for records.

    Returns:
        str: UUID4 string suitable for use as primary key.
    """
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """Get current timestamp in UTC.

    Returns:
        datetime: Current UTC timestamp for record creation/updates.
    """
    return datetime.now(timezone.utc)


class BaseDataProcessor:
    """
    Base data processor for JSON field handling.

    Provides utility methods for safely parsing and handling JSON data in database
    fields, with fallback support for invalid or missing data.
    """

    @staticmethod
    def safe_json_loads(data: Any, fallback: Any = None) -> Any:
        """Safely parse JSON data with fallback handling.

        Args:
            data: JSON string to parse, or None/empty value.
            fallback: Value to return if parsing fails or data is empty.

        Returns:
            Parsed JSON data (typically list or dict), or fallback value.
        """
        if not data:
            return fallback if fallback is not None else []
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return fallback if fallback is not None else []


# Common check constraints
PRIORITY_CONSTRAINT = CheckConstraint(
    "priority IN ('low', 'medium', 'high', 'critical')", name="check_priority"
)

TASK_STATUS_CONSTRAINT = CheckConstraint(
    "status IN ('pending', 'in-progress', 'blocked', 'done', 'cancelled')",
    name="check_task_status",
)

CAMPAIGN_STATUS_CONSTRAINT = CheckConstraint(
    "status IN ('planning', 'active', 'paused', 'completed', 'cancelled')",
    name="check_campaign_status",
)

MEMORY_SESSION_STATUS_CONSTRAINT = CheckConstraint(
    "status IN ('active', 'completed', 'archived')",
    name="check_session_status",
)


def model_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert SQLAlchemy model instance to dictionary representation."""
    result = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            result[column.name] = value.isoformat() if value else None
        else:
            result[column.name] = value
    return result


def get_json_field(instance: Any, field_name: str, fallback: Any = None) -> Any:
    """Get a JSON field as parsed data."""
    field_value = getattr(instance, field_name, None)
    return BaseDataProcessor.safe_json_loads(field_value, fallback=fallback)


def set_json_field(instance: Any, field_name: str, data: Any) -> None:
    """Set a JSON field from data."""
    setattr(instance, field_name, json.dumps(data) if data else None)
