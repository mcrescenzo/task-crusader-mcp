"""
Campaign Specification Domain Entities.

Dataclasses for representing campaign and task specifications
used in bulk creation operations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResearchSpec:
    """Specification for a research item."""

    content: str
    research_type: str = "findings"  # findings, approaches, docs, strategy, analysis, requirements

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchSpec":
        """Create ResearchSpec from dictionary."""
        return cls(
            content=data.get("content", ""),
            research_type=data.get("type", data.get("research_type", "findings")),
        )


@dataclass
class TaskSpec:
    """
    Specification for a task to be created.

    Uses temp_id for internal references before UUIDs are assigned.
    """

    temp_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    task_type: str = "code"
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # List of temp_ids
    acceptance_criteria: List[str] = field(default_factory=list)
    research: List[ResearchSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpec":
        """Create TaskSpec from dictionary."""
        research_list = [
            ResearchSpec.from_dict(r) if isinstance(r, dict) else ResearchSpec(content=str(r))
            for r in data.get("research", [])
        ]

        return cls(
            temp_id=data.get("temp_id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            status=data.get("status", "pending"),
            task_type=data.get("type", data.get("task_type", "code")),
            category=data.get("category"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            research=research_list,
        )


@dataclass
class CampaignSpec:
    """
    Specification for a campaign with tasks to be created atomically.

    Contains all data needed to create a campaign and its tasks
    in a single transaction.
    """

    name: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "planning"
    metadata: Dict[str, Any] = field(default_factory=dict)
    research: List[ResearchSpec] = field(default_factory=list)
    tasks: List[TaskSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignSpec":
        """
        Create CampaignSpec from dictionary.

        Expected format:
        {
            "campaign": {
                "name": "...",
                "description": "...",
                "priority": "...",
                "research": [...]
            },
            "tasks": [
                {"temp_id": "t1", "title": "...", ...},
                ...
            ]
        }
        """
        campaign_data = data.get("campaign", data)  # Support both nested and flat

        research_list = [
            ResearchSpec.from_dict(r) if isinstance(r, dict) else ResearchSpec(content=str(r))
            for r in campaign_data.get("research", [])
        ]

        tasks_list = [TaskSpec.from_dict(t) for t in data.get("tasks", [])]

        return cls(
            name=campaign_data.get("name", ""),
            description=campaign_data.get("description"),
            priority=campaign_data.get("priority", "medium"),
            status=campaign_data.get("status", "planning"),
            metadata=campaign_data.get("metadata", {}),
            research=research_list,
            tasks=tasks_list,
        )

    def get_temp_ids(self) -> List[str]:
        """Get all task temp_ids."""
        return [task.temp_id for task in self.tasks]

    def get_task_by_temp_id(self, temp_id: str) -> Optional[TaskSpec]:
        """Get a task by its temp_id."""
        for task in self.tasks:
            if task.temp_id == temp_id:
                return task
        return None
