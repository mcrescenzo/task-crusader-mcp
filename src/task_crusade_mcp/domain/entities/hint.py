"""
Hint Entity - Context-aware guidance for AI agents.

Hints provide dynamic "next step" guidance based on operation results
and current state, helping agents navigate the task execution workflow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class HintCategory(Enum):
    """Categories of hints for filtering and organization."""

    WORKFLOW = "workflow"  # Next action guidance
    COORDINATION = "coordination"  # Multi-agent awareness
    PROGRESS = "progress"  # Progress updates
    COMPLETION = "completion"  # Task/campaign completion


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
        Get the primary (first workflow) tool call.

        Returns the tool_call from the first WORKFLOW hint,
        or the first hint with a tool_call if no workflow hints exist.
        """
        # Prefer workflow hints
        for hint in self.hints:
            if hint.category == HintCategory.WORKFLOW and hint.tool_call:
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
