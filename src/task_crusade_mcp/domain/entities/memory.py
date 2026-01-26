"""
Memory Domain DTOs - Data Transfer Objects for Memory entities.

This module provides domain-level DTOs for memory entities, sessions, and associations,
establishing proper hexagonal architecture boundaries between application and database layers.

Memory is used internally for task operations like acceptance criteria, research items,
implementation notes, and testing steps. It is NOT exposed via MCP tools.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntityDTO:
    """
    Domain DTO for Memory Entity.

    Represents a knowledge graph node with typed observations.
    Used internally for storing task acceptance criteria, research, notes, etc.
    """

    id: str
    session_id: str
    name: str
    entity_type: str
    observations: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value for key with optional default if key not found."""
        return self.to_dict().get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "observations": self.observations,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntityDTO":
        """Create DTO from dictionary representation."""
        # Parse created_at (required field)
        created_at_raw = data.get("created_at")
        created_at: datetime
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(timezone.utc)  # Default if missing

        # Parse updated_at (optional field)
        updated_at_raw = data.get("updated_at")
        if isinstance(updated_at_raw, str):
            updated_at = datetime.fromisoformat(updated_at_raw)
        elif isinstance(updated_at_raw, datetime):
            updated_at = updated_at_raw
        else:
            updated_at = None

        return cls(
            id=data["id"],
            session_id=data["session_id"],
            name=data["name"],
            entity_type=data["entity_type"],
            observations=data.get("observations", []),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class MemorySessionDTO:
    """
    Domain DTO for Memory Session.

    Represents a memory session with lifecycle management.
    Sessions organize related memory entities.
    """

    id: str
    name: Optional[str]
    status: str
    workflow_type: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value for key with optional default if key not found."""
        return self.to_dict().get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "workflow_type": self.workflow_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemorySessionDTO":
        """Create DTO from dictionary representation."""
        # Parse created_at (required field)
        created_at_raw = data.get("created_at")
        created_at: datetime
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(timezone.utc)  # Default if missing

        # Parse optional datetime fields
        def parse_optional_datetime(value: Any) -> Optional[datetime]:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            elif isinstance(value, datetime):
                return value
            return None

        return cls(
            id=data["id"],
            name=data.get("name"),
            status=data["status"],
            workflow_type=data.get("workflow_type"),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=parse_optional_datetime(data.get("updated_at")),
            completed_at=parse_optional_datetime(data.get("completed_at")),
            archived_at=parse_optional_datetime(data.get("archived_at")),
        )


@dataclass
class MemoryTaskAssociationDTO:
    """
    Domain DTO for Memory Task Association.

    Represents a link between memory entities and tasks/campaigns.
    Used for storing acceptance criteria, research, implementation notes, and testing steps.
    """

    id: str
    memory_entity_id: str
    task_id: Optional[str]
    campaign_id: Optional[str]
    association_type: str
    notes: Optional[str]
    order_index: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value for key with optional default if key not found."""
        return self.to_dict().get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        return {
            "id": self.id,
            "memory_entity_id": self.memory_entity_id,
            "task_id": self.task_id,
            "campaign_id": self.campaign_id,
            "association_type": self.association_type,
            "notes": self.notes,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryTaskAssociationDTO":
        """Create DTO from dictionary representation."""
        # Parse created_at (required field)
        created_at_raw = data.get("created_at")
        created_at: datetime
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(timezone.utc)  # Default if missing

        # Parse updated_at (optional field)
        updated_at_raw = data.get("updated_at")
        if isinstance(updated_at_raw, str):
            updated_at = datetime.fromisoformat(updated_at_raw)
        elif isinstance(updated_at_raw, datetime):
            updated_at = updated_at_raw
        else:
            updated_at = None

        return cls(
            id=data["id"],
            memory_entity_id=data["memory_entity_id"],
            task_id=data.get("task_id"),
            campaign_id=data.get("campaign_id"),
            association_type=data["association_type"],
            notes=data.get("notes"),
            order_index=data.get("order_index", 0),
            created_at=created_at,
            updated_at=updated_at,
        )


# Valid association types for task operations
VALID_ASSOCIATION_TYPES = {
    "findings",
    "context",
    "reference",
    "research",
    "analysis",
    "implementation_note",
    "acceptance_criteria",
    "risk",
    "testing_step",
}

# Entity type constants for task-related memory entities
ENTITY_TYPE_ACCEPTANCE_CRITERIA = "acceptance_criteria"
ENTITY_TYPE_RESEARCH_ITEM = "research_item"
ENTITY_TYPE_IMPLEMENTATION_NOTE = "implementation_note"
ENTITY_TYPE_TESTING_STEP = "testing_step"
