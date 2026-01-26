"""
Campaign Domain Entity (DTO).

Data Transfer Object for Campaign entity, providing a clean interface between
the application layer and database layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class CampaignDTO:
    """
    Campaign Data Transfer Object.

    Represents a campaign entity in the domain layer, providing a clean
    interface for campaign data without ORM dependencies.

    Attributes:
        id: Unique campaign identifier (UUID)
        name: Campaign name (unique)
        description: Detailed campaign description
        status: Campaign status ('planning', 'active', 'paused', 'completed', 'cancelled')
        priority: Priority level ('low', 'medium', 'high', 'critical')
        created_at: Campaign creation timestamp
        updated_at: Last modification timestamp
        completed_at: Campaign completion timestamp (optional)
        metadata: Extensible campaign metadata dictionary
    """

    id: str
    name: str
    description: Optional[str] = None
    status: str = "planning"
    priority: str = "medium"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> Optional[str]:
        """Get campaign title from metadata."""
        return self.metadata.get("title")

    @property
    def owner(self) -> Optional[str]:
        """Get campaign owner from metadata."""
        return self.metadata.get("owner")

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key with optional default for backward compatibility."""
        return self.to_dict().get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "title": self.title,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignDTO":
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

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            status=data.get("status", "planning"),
            priority=data.get("priority", "medium"),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            metadata=data.get("metadata", {}),
        )
