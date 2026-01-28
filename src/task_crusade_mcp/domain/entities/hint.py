"""
Hint Entity - Context-aware guidance for AI agents.

Hints provide dynamic "next step" guidance based on operation results
and current state, helping agents navigate the task execution workflow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class HintCategory(Enum):
    """
    Categories of hints for filtering and organization.

    Priority order (highest to lowest):
    1. WORKFLOW - immediate next action
    2. QUALITY - setup/completeness issues
    3. COORDINATION - dependency/blocking issues
    4. PROGRESS - status updates
    5. COMPLETION - end-state guidance
    """

    WORKFLOW = "workflow"  # Next action guidance
    QUALITY = "quality"  # Task/campaign completeness issues
    COORDINATION = "coordination"  # Multi-agent awareness
    PROGRESS = "progress"  # Progress updates
    COMPLETION = "completion"  # Task/campaign completion


class CampaignSetupStage(Enum):
    """
    Stages of campaign setup for progressive guidance.

    Campaigns progress through these stages:
    CREATED -> TASKS_ADDED -> CRITERIA_DEFINED -> TESTING_PLANNED -> EXECUTING -> COMPLETED
    """

    CREATED = "created"  # Campaign created, no tasks
    TASKS_ADDED = "tasks_added"  # Tasks exist but need criteria
    CRITERIA_DEFINED = "criteria_defined"  # All tasks have criteria, need testing
    TESTING_PLANNED = "testing_planned"  # Ready for execution
    EXECUTING = "executing"  # Campaign in progress
    COMPLETED = "completed"  # All tasks done


@dataclass
class TaskCompletenessInfo:
    """
    Information about a task's completeness for quality hints.

    Used by HintGenerator to determine what guidance to provide
    based on what's missing from a task definition.
    """

    task_id: str
    task_title: str
    task_status: str
    has_acceptance_criteria: bool
    criteria_count: int
    has_testing_strategy: bool
    testing_steps_count: int
    has_research: bool

    @property
    def missing_items(self) -> List[str]:
        """Returns list of missing items in priority order."""
        missing = []
        if not self.has_acceptance_criteria:
            missing.append("acceptance_criteria")
        if not self.has_testing_strategy:
            missing.append("testing_strategy")
        if not self.has_research:
            missing.append("research")
        return missing

    @property
    def is_complete(self) -> bool:
        """Check if task has all quality items defined."""
        return self.has_acceptance_criteria and self.has_testing_strategy


@dataclass
class CampaignHealthInfo:
    """
    Information about campaign health for quality hints.

    Used by HintGenerator to evaluate campaign readiness
    and provide guidance on what needs improvement.
    """

    campaign_id: str
    campaign_name: str
    total_tasks: int
    tasks_without_criteria: int
    tasks_without_testing: int
    first_task_without_criteria_id: Optional[str]
    first_task_without_testing_id: Optional[str]
    tasks_complete: int
    tasks_in_progress: int
    tasks_blocked: int
    tasks_pending: int

    @property
    def is_ready_for_execution(self) -> bool:
        """Check if campaign is ready to start execution."""
        return self.total_tasks > 0 and self.tasks_without_criteria == 0

    @property
    def health_score(self) -> float:
        """Calculate campaign health as percentage (0-100)."""
        if self.total_tasks == 0:
            return 0.0
        tasks_with_criteria = self.total_tasks - self.tasks_without_criteria
        tasks_with_testing = self.total_tasks - self.tasks_without_testing
        # Weight: 60% criteria, 40% testing
        criteria_score = (tasks_with_criteria / self.total_tasks) * 60
        testing_score = (tasks_with_testing / self.total_tasks) * 40
        return round(criteria_score + testing_score, 1)

    @property
    def completion_rate(self) -> float:
        """Calculate task completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return round((self.tasks_complete / self.total_tasks) * 100, 1)


@dataclass
class Hint:
    """
    Single actionable hint for agent guidance.

    Each hint tells the agent exactly what to do next, with a copy-pasteable
    tool call that includes actual IDs from the current context.

    Attributes:
        category: Type of hint (workflow, coordination, progress, completion)
        message: Human-readable message describing the hint
        tool_call: Copy-pasteable tool call string (e.g., "task_create(campaign_id='abc')")
        context: Additional context data (IDs, counts, etc.)
    """

    category: HintCategory
    message: str
    tool_call: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert hint to dictionary for serialization."""
        return {
            "category": self.category.value,
            "message": self.message,
            "tool_call": self.tool_call,
            "context": self.context,
        }


@dataclass
class HintCollection:
    """
    Collection of hints with utility methods.

    Provides a convenient container for multiple hints with
    methods for formatting and extracting the primary action.
    """

    hints: List[Hint]

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert all hints to list of dictionaries."""
        return [hint.to_dict() for hint in self.hints]

    def get_primary_tool_call(self) -> Optional[str]:
        """
        Get the primary tool call based on category priority.

        Priority order: WORKFLOW > QUALITY > COORDINATION > PROGRESS > COMPLETION

        Returns the tool_call from the highest priority hint,
        or the first hint with a tool_call if none in priority categories.
        """
        # Priority order for tool call selection
        priority_order = [
            HintCategory.WORKFLOW,
            HintCategory.QUALITY,
            HintCategory.COORDINATION,
            HintCategory.PROGRESS,
            HintCategory.COMPLETION,
        ]

        # Check each category in priority order
        for category in priority_order:
            for hint in self.hints:
                if hint.category == category and hint.tool_call:
                    return hint.tool_call

        # Fall back to any hint with a tool_call
        for hint in self.hints:
            if hint.tool_call:
                return hint.tool_call

        return None

    def is_empty(self) -> bool:
        """Check if collection has no hints."""
        return len(self.hints) == 0

    def __len__(self) -> int:
        """Return number of hints."""
        return len(self.hints)
