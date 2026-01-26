"""
Task Domain Entity (DTO).

Data Transfer Object for Task entity, providing a clean interface between
the application layer and database layer.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TaskDTO:
    """
    Task Data Transfer Object.

    Represents a task entity in the domain layer, providing a clean
    interface for task data without ORM dependencies.

    Attributes:
        id: Unique task identifier (UUID)
        title: Task title (required)
        description: Detailed task description
        priority: Priority level ('low', 'medium', 'high', 'critical')
        status: Current status ('pending', 'in-progress', 'blocked', 'done', 'cancelled')
        category: Task category for organization
        type: Task type ('code', 'research', 'test', 'documentation', 'refactor', 'deployment', 'review')
        created_at: Task creation timestamp
        updated_at: Last modification timestamp
        completed_at: Task completion timestamp (optional)
        tags: List of tags for categorization
        dependencies: List of task IDs this task depends on
        failure_reason: Reason for last failure if applicable
        campaign_id: Foreign key to associated campaign
        priority_order: Priority order for sorting within campaign
    """

    id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    category: Optional[str] = None
    type: str = "code"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    failure_reason: Optional[str] = None
    campaign_id: Optional[str] = None
    priority_order: Optional[int] = None

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value by key with optional default for backward compatibility."""
        return self.to_dict().get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "category": self.category,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "failure_reason": self.failure_reason,
            "campaign_id": self.campaign_id,
            "priority_order": self.priority_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDTO":
        """Create DTO from dictionary representation."""
        # Parse datetime fields if they are strings
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        # Handle tags and dependencies (may be JSON strings or lists)
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags) if tags else []

        dependencies = data.get("dependencies", [])
        if isinstance(dependencies, str):
            dependencies = json.loads(dependencies) if dependencies else []

        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            status=data.get("status", "pending"),
            category=data.get("category"),
            type=data.get("type", "code"),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            tags=tags,
            dependencies=dependencies,
            failure_reason=data.get("failure_reason"),
            campaign_id=data.get("campaign_id"),
            priority_order=data.get("priority_order"),
        )
