"""
Hint Generator - Context-aware guidance for AI agents.

Generates dynamic "next step" hints based on operation results and current state.
This is a lightweight implementation focused on actionable guidance.
"""

import logging
from typing import Any, Dict, List, Optional

from task_crusade_mcp.domain.entities.hint import Hint, HintCategory, HintCollection

logger = logging.getLogger(__name__)


class HintGenerator:
    """
    Generates context-aware hints based on operation results.

    This is a stateless service that analyzes operation outcomes
    and current state to provide actionable guidance to AI agents.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize hint generator.

        Args:
            enabled: Whether hints are enabled. If False, all methods return empty collections.
        """
        self.enabled = enabled

    def _empty(self) -> HintCollection:
        """Return empty hint collection."""
        return HintCollection(hints=[])

    # --- Campaign Operation Hints ---

    def post_campaign_create(
        self,
        campaign_id: str,
        campaign_name: str,
    ) -> HintCollection:
        """
        Generate hints after campaign creation.

        Args:
            campaign_id: ID of the created campaign
            campaign_name: Name of the created campaign

        Returns:
            HintCollection with next step guidance
        """
        if not self.enabled:
            return self._empty()

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Campaign '{campaign_name}' created. Add tasks to begin.",
                    tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                    context={"campaign_id": campaign_id},
                )
            ]
        )

    def post_campaign_progress(
        self,
        campaign_id: str,
        progress_data: Dict[str, Any],
    ) -> HintCollection:
        """
        Generate hints based on campaign progress state.

        Args:
            campaign_id: Campaign ID
            progress_data: Progress summary with tasks_by_status, completion_rate, etc.

        Returns:
            HintCollection with progress-based guidance
        """
        if not self.enabled:
            return self._empty()

        tasks_by_status = progress_data.get("tasks_by_status", {})
        pending = tasks_by_status.get("pending", 0)
        in_progress = tasks_by_status.get("in-progress", 0)
        done = tasks_by_status.get("done", 0)
        blocked = tasks_by_status.get("blocked", 0)
        total = progress_data.get("total_tasks", 0)
        completion_rate = progress_data.get("completion_rate", 0)

        hints: List[Hint] = []

        if total == 0:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Campaign has no tasks. Add tasks to begin.",
                    tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                    context={"campaign_id": campaign_id},
                )
            )
        elif pending == 0 and in_progress == 0 and blocked == 0:
            # All done
            hints.append(
                Hint(
                    category=HintCategory.COMPLETION,
                    message=f"Campaign complete! All {done} tasks done.",
                    tool_call=f"campaign_update(campaign_id='{campaign_id}', status='completed')",
                    context={"campaign_id": campaign_id, "done": done},
                )
            )
        elif pending > 0 or in_progress > 0:
            hints.append(
                Hint(
                    category=HintCategory.PROGRESS,
                    message=f"Progress: {done}/{total} done ({completion_rate:.0f}%). "
                    f"{pending} pending, {in_progress} in-progress, {blocked} blocked.",
                    tool_call=f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')",
                    context={
                        "campaign_id": campaign_id,
                        "done": done,
                        "pending": pending,
                        "in_progress": in_progress,
                        "blocked": blocked,
                    },
                )
            )

        return HintCollection(hints=hints)

    # --- Task Operation Hints ---

    def post_task_create(
        self,
        task_id: str,
        task_title: str,
        campaign_id: str,
        has_acceptance_criteria: bool,
        criteria_count: int = 0,
    ) -> HintCollection:
        """
        Generate hints after task creation.

        Args:
            task_id: ID of the created task
            task_title: Title of the task
            campaign_id: Parent campaign ID
            has_acceptance_criteria: Whether task has acceptance criteria
            criteria_count: Number of acceptance criteria

        Returns:
            HintCollection with next step guidance
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if not has_acceptance_criteria:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Task '{task_title}' created. Add acceptance criteria to define completion.",
                    tool_call=f"task_acceptance_criteria_add(task_id='{task_id}', content='...')",
                    context={"task_id": task_id, "campaign_id": campaign_id},
                )
            )
        else:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Task '{task_title}' created with {criteria_count} criteria. Ready for execution.",
                    tool_call=f"task_update(task_id='{task_id}', status='in-progress')",
                    context={
                        "task_id": task_id,
                        "campaign_id": campaign_id,
                        "criteria_count": criteria_count,
                    },
                )
            )

        return HintCollection(hints=hints)

    def post_task_status_change(
        self,
        task_id: str,
        task_title: str,
        campaign_id: str,
        old_status: str,
        new_status: str,
        criteria_count: int = 0,
        unmet_criteria_count: int = 0,
    ) -> HintCollection:
        """
        Generate hints after task status change.

        Args:
            task_id: Task ID
            task_title: Task title
            campaign_id: Parent campaign ID
            old_status: Previous status
            new_status: New status
            criteria_count: Total acceptance criteria count
            unmet_criteria_count: Number of unmet criteria

        Returns:
            HintCollection with status-specific guidance
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if new_status == "in-progress":
            if criteria_count > 0:
                hints.append(
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Task '{task_title}' started. {criteria_count} criteria to satisfy.",
                        tool_call=None,  # Agent should implement the task
                        context={
                            "task_id": task_id,
                            "criteria_count": criteria_count,
                            "unmet_count": unmet_criteria_count,
                        },
                    )
                )
            else:
                hints.append(
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Task '{task_title}' started. Consider adding acceptance criteria.",
                        tool_call=f"task_acceptance_criteria_add(task_id='{task_id}', content='...')",
                        context={"task_id": task_id},
                    )
                )
        elif new_status == "blocked":
            hints.append(
                Hint(
                    category=HintCategory.COORDINATION,
                    message=f"Task '{task_title}' is now blocked. Resolve dependencies to continue.",
                    tool_call=f"task_show(task_id='{task_id}')",
                    context={"task_id": task_id},
                )
            )

        return HintCollection(hints=hints)

    def post_task_complete(
        self,
        task_id: str,
        task_title: str,
        campaign_id: str,
        campaign_progress: Optional[Dict[str, Any]] = None,
    ) -> HintCollection:
        """
        Generate hints after task completion.

        Args:
            task_id: Completed task ID
            task_title: Task title
            campaign_id: Parent campaign ID
            campaign_progress: Optional progress data (tasks_by_status, completion_rate)

        Returns:
            HintCollection with next task or completion guidance
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if campaign_progress:
            tasks_by_status = campaign_progress.get("tasks_by_status", {})
            pending = tasks_by_status.get("pending", 0)
            in_progress = tasks_by_status.get("in-progress", 0)
            blocked = tasks_by_status.get("blocked", 0)
            done = tasks_by_status.get("done", 0)
            total = campaign_progress.get("total_tasks", 0)
            completion_rate = campaign_progress.get("completion_rate", 0)

            remaining = pending + in_progress + blocked

            if remaining == 0:
                hints.append(
                    Hint(
                        category=HintCategory.COMPLETION,
                        message=f"Task '{task_title}' complete. Campaign finished! All {done} tasks done.",
                        tool_call=f"campaign_update(campaign_id='{campaign_id}', status='completed')",
                        context={"campaign_id": campaign_id, "done": done},
                    )
                )
            else:
                hints.append(
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Task '{task_title}' complete ({done}/{total}, {completion_rate:.0f}%). "
                        f"{pending} pending, {blocked} blocked.",
                        tool_call=f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')",
                        context={
                            "campaign_id": campaign_id,
                            "done": done,
                            "pending": pending,
                            "blocked": blocked,
                        },
                    )
                )
        else:
            # No progress data - generic hint
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Task '{task_title}' complete. Get next task.",
                    tool_call=f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')",
                    context={"campaign_id": campaign_id, "task_id": task_id},
                )
            )

        return HintCollection(hints=hints)

    # --- Actionable Task Hints ---

    def actionable_task_hints(
        self,
        task_data: Optional[Dict[str, Any]],
        campaign_id: str,
        campaign_progress: Optional[Dict[str, Any]] = None,
        no_actionable: bool = False,
    ) -> HintCollection:
        """
        Generate hints when retrieving actionable tasks.

        Args:
            task_data: Task data if found (id, title, acceptance_criteria_details)
            campaign_id: Campaign ID
            campaign_progress: Optional progress data
            no_actionable: True if no actionable task was found

        Returns:
            HintCollection with execution guidance or blocked status
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if no_actionable or task_data is None:
            # No actionable task found
            if campaign_progress:
                tasks_by_status = campaign_progress.get("tasks_by_status", {})
                pending = tasks_by_status.get("pending", 0)
                blocked = tasks_by_status.get("blocked", 0)
                done = tasks_by_status.get("done", 0)

                if pending == 0 and blocked == 0:
                    hints.append(
                        Hint(
                            category=HintCategory.COMPLETION,
                            message=f"No actionable tasks. Campaign complete with {done} tasks done.",
                            tool_call=f"campaign_update(campaign_id='{campaign_id}', status='completed')",
                            context={"campaign_id": campaign_id},
                        )
                    )
                elif blocked > 0:
                    hints.append(
                        Hint(
                            category=HintCategory.COORDINATION,
                            message=f"No actionable tasks. {blocked} tasks blocked by dependencies.",
                            tool_call=f"task_list(campaign_id='{campaign_id}', status='blocked')",
                            context={"campaign_id": campaign_id, "blocked": blocked},
                        )
                    )
                else:
                    hints.append(
                        Hint(
                            category=HintCategory.COORDINATION,
                            message="No actionable tasks available.",
                            tool_call=f"campaign_get_progress_summary(campaign_id='{campaign_id}')",
                            context={"campaign_id": campaign_id},
                        )
                    )
            else:
                hints.append(
                    Hint(
                        category=HintCategory.COORDINATION,
                        message="No actionable tasks available.",
                        tool_call=f"campaign_get_progress_summary(campaign_id='{campaign_id}')",
                        context={"campaign_id": campaign_id},
                    )
                )
        else:
            # Task found
            task_id = task_data.get("id", "")
            task_title = task_data.get("title", "Unknown")
            criteria = task_data.get("acceptance_criteria_details", [])
            criteria_count = len(criteria) if criteria else 0

            # Extract criteria IDs for convenience
            criteria_ids = [c.get("id") for c in criteria if c.get("id")] if criteria else []

            if criteria_count > 0:
                hints.append(
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Next task: '{task_title}' ({criteria_count} criteria).",
                        tool_call=f"task_update(task_id='{task_id}', status='in-progress')",
                        context={
                            "task_id": task_id,
                            "criteria_count": criteria_count,
                            "criteria_ids": criteria_ids,
                        },
                    )
                )
            else:
                hints.append(
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Next task: '{task_title}' (no acceptance criteria).",
                        tool_call=f"task_update(task_id='{task_id}', status='in-progress')",
                        context={"task_id": task_id},
                    )
                )

        return HintCollection(hints=hints)

    # --- Acceptance Criteria Hints ---

    def post_criteria_met(
        self,
        task_id: str,
        task_title: str,
        criteria_id: str,
        met_count: int,
        total_count: int,
    ) -> HintCollection:
        """
        Generate hints after marking criteria as met.

        Args:
            task_id: Task ID
            task_title: Task title
            criteria_id: Marked criteria ID
            met_count: Number of criteria now met
            total_count: Total criteria count

        Returns:
            HintCollection with progress or completion guidance
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if met_count >= total_count:
            # All criteria met
            hints.append(
                Hint(
                    category=HintCategory.COMPLETION,
                    message=f"All {total_count} criteria met for '{task_title}'!",
                    tool_call=f"task_complete(task_id='{task_id}')",
                    context={
                        "task_id": task_id,
                        "met_count": met_count,
                        "total_count": total_count,
                    },
                )
            )
        else:
            # More criteria remain
            remaining = total_count - met_count
            hints.append(
                Hint(
                    category=HintCategory.PROGRESS,
                    message=f"Criteria {met_count}/{total_count} met for '{task_title}'. {remaining} remaining.",
                    tool_call=None,  # Agent should continue implementing
                    context={
                        "task_id": task_id,
                        "met_count": met_count,
                        "total_count": total_count,
                        "remaining": remaining,
                    },
                )
            )

        return HintCollection(hints=hints)

    def post_criteria_unmet(
        self,
        task_id: str,
        task_title: str,
        criteria_id: str,
        met_count: int,
        total_count: int,
    ) -> HintCollection:
        """
        Generate hints after marking criteria as unmet.

        Args:
            task_id: Task ID
            task_title: Task title
            criteria_id: Unmarked criteria ID
            met_count: Number of criteria now met
            total_count: Total criteria count

        Returns:
            HintCollection with progress guidance
        """
        if not self.enabled:
            return self._empty()

        remaining = total_count - met_count

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.PROGRESS,
                    message=f"Criteria unmarked. {met_count}/{total_count} met for '{task_title}'. "
                    f"{remaining} remaining.",
                    tool_call=None,
                    context={
                        "task_id": task_id,
                        "met_count": met_count,
                        "total_count": total_count,
                        "remaining": remaining,
                    },
                )
            ]
        )

    # --- Utility Methods ---

    def format_for_response(
        self,
        hints: HintCollection,
    ) -> Dict[str, Any]:
        """
        Format hints for inclusion in service response.

        Returns a dictionary with 'hints' list and 'next_action' string
        suitable for merging into response data.

        Args:
            hints: HintCollection to format

        Returns:
            Dict with 'hints' and optional 'next_action' keys
        """
        if hints.is_empty():
            return {}

        result: Dict[str, Any] = {"hints": hints.to_list()}

        primary = hints.get_primary_tool_call()
        if primary:
            result["next_action"] = primary

        return result
