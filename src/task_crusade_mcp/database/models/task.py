"""
Task SQLAlchemy Model.

Represents a task - an individual unit of work within a campaign.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from task_crusade_mcp.database.models.base import (
    PRIORITY_CONSTRAINT,
    TASK_STATUS_CONSTRAINT,
    Base,
    generate_id,
    get_current_timestamp,
)


class Task(Base):
    """
    Task model representing an individual unit of work.

    Tasks belong to campaigns and can have dependencies on other tasks.
    """

    __tablename__ = "tasks"

    id: str = Column(String(36), primary_key=True, default=generate_id)
    title: str = Column(String(255), nullable=False, index=True)
    description: Optional[str] = Column(Text, nullable=True)
    priority: str = Column(String(20), nullable=False, default="medium")
    status: str = Column(String(20), nullable=False, default="pending")
    category: Optional[str] = Column(String(100), nullable=True)
    type: str = Column(String(50), nullable=False, default="code")
    tags_json: Optional[str] = Column("tags", Text, nullable=True)
    dependencies_json: Optional[str] = Column("dependencies", Text, nullable=True)
    failure_reason: Optional[str] = Column(Text, nullable=True)
    priority_order: Optional[int] = Column(Integer, nullable=True)
    campaign_id: Optional[str] = Column(
        String(36), ForeignKey("campaigns.id"), nullable=True, index=True
    )
    created_at: datetime = Column(DateTime, nullable=False, default=get_current_timestamp)
    updated_at: datetime = Column(
        DateTime, nullable=False, default=get_current_timestamp, onupdate=get_current_timestamp
    )
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)

    # Table-level constraints
    __table_args__ = (
        TASK_STATUS_CONSTRAINT,
        PRIORITY_CONSTRAINT,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="tasks")

    def get_tags(self) -> List[str]:
        """Get tags as list."""
        if not self.tags_json:
            return []
        try:
            return json.loads(self.tags_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: List[str]) -> None:
        """Set tags from list."""
        self.tags_json = json.dumps(tags) if tags else None

    def get_dependencies(self) -> List[str]:
        """Get dependencies as list."""
        if not self.dependencies_json:
            return []
        try:
            return json.loads(self.dependencies_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_dependencies(self, dependencies: List[str]) -> None:
        """Set dependencies from list."""
        self.dependencies_json = json.dumps(dependencies) if dependencies else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "category": self.category,
            "type": self.type,
            "tags": self.get_tags(),
            "dependencies": self.get_dependencies(),
            "failure_reason": self.failure_reason,
            "priority_order": self.priority_order,
            "campaign_id": self.campaign_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self) -> str:
        return f"<Task(id={self.id!r}, title={self.title!r}, status={self.status!r})>"
