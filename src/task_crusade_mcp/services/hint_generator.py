"""
Hint Generator - Context-aware guidance for AI agents.

Generates dynamic "next step" hints based on operation results and current state.
This is a lightweight implementation focused on actionable guidance.
"""

import logging
from typing import Any, Dict, List, Optional

from task_crusade_mcp.domain.entities.hint import (
    CampaignHealthInfo,
    CampaignSetupStage,
    Hint,
    HintCategory,
    HintCollection,
    TaskCompletenessInfo,
)

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
        blocking_tasks: Optional[List[Dict[str, Any]]] = None,
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
            blocking_tasks: Optional list of tasks blocking this one (for blocked status)

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
            if blocking_tasks and len(blocking_tasks) > 0:
                # Format blocking task info
                blocking_titles = [t.get("title", "Unknown") for t in blocking_tasks[:3]]
                titles_str = ", ".join(blocking_titles)
                if len(blocking_tasks) > 3:
                    titles_str += f" (+{len(blocking_tasks) - 3} more)"
                first_blocker_id = blocking_tasks[0].get("id", "")

                hints.append(
                    Hint(
                        category=HintCategory.COORDINATION,
                        message=f"Task '{task_title}' blocked by: {titles_str}. Complete those first.",
                        tool_call=f"task_show(task_id='{first_blocker_id}')",
                        context={
                            "task_id": task_id,
                            "blocking_task_ids": [t.get("id") for t in blocking_tasks],
                        },
                    )
                )
            else:
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

    # --- Task Memory Operations Hints ---

    def post_acceptance_criteria_add(
        self,
        task_id: str,
        task_title: str,
        criteria_count: int,
    ) -> HintCollection:
        """
        Generate hints after adding acceptance criteria.

        Args:
            task_id: Task ID
            task_title: Task title
            criteria_count: Total criteria count after addition

        Returns:
            HintCollection with workflow guidance
        """
        if not self.enabled:
            return self._empty()

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Criterion added ({criteria_count} total for '{task_title}'). "
                    "Add more criteria or start working.",
                    tool_call=f"task_update(task_id='{task_id}', status='in-progress')",
                    context={
                        "task_id": task_id,
                        "criteria_count": criteria_count,
                    },
                )
            ]
        )

    def post_research_add(
        self,
        task_id: str,
        task_title: str,
        research_type: str,
    ) -> HintCollection:
        """
        Generate hints after adding research to a task.

        Args:
            task_id: Task ID
            task_title: Task title
            research_type: Type of research added

        Returns:
            HintCollection with progress guidance
        """
        if not self.enabled:
            return self._empty()

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.PROGRESS,
                    message=f"Research recorded for '{task_title}'. Continue implementing.",
                    tool_call=None,  # Agent should continue work
                    context={
                        "task_id": task_id,
                        "research_type": research_type,
                    },
                )
            ]
        )

    def post_implementation_note_add(
        self,
        task_id: str,
        task_title: str,
        unmet_criteria: Optional[List[Dict[str, Any]]] = None,
    ) -> HintCollection:
        """
        Generate hints after adding an implementation note.

        Args:
            task_id: Task ID
            task_title: Task title
            unmet_criteria: Optional list of unmet acceptance criteria

        Returns:
            HintCollection with workflow guidance
        """
        if not self.enabled:
            return self._empty()

        if unmet_criteria and len(unmet_criteria) > 0:
            first_criteria_id = unmet_criteria[0].get("id", "")
            return HintCollection(
                hints=[
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Implementation note added for '{task_title}'. "
                        "Mark criteria as you complete them.",
                        tool_call=f"task_acceptance_criteria_mark_met(criteria_id='{first_criteria_id}')",
                        context={
                            "task_id": task_id,
                            "unmet_count": len(unmet_criteria),
                            "criteria_ids": [c.get("id") for c in unmet_criteria],
                        },
                    )
                ]
            )
        else:
            return HintCollection(
                hints=[
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message=f"Implementation note added for '{task_title}'. "
                        "Continue implementing.",
                        tool_call=None,
                        context={"task_id": task_id},
                    )
                ]
            )

    def post_testing_step_add(
        self,
        task_id: str,
        task_title: str,
        step_type: str,
    ) -> HintCollection:
        """
        Generate hints after adding a testing step.

        Args:
            task_id: Task ID
            task_title: Task title
            step_type: Type of testing step added

        Returns:
            HintCollection with workflow guidance
        """
        if not self.enabled:
            return self._empty()

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Testing step added for '{task_title}'. "
                    "Run tests to verify implementation.",
                    tool_call=None,  # Agent should run tests
                    context={
                        "task_id": task_id,
                        "step_type": step_type,
                    },
                )
            ]
        )

    # --- Campaign Memory Operations Hints ---

    def post_campaign_research_add(
        self,
        campaign_id: str,
        campaign_name: str,
        research_type: str,
        task_count: int = 0,
    ) -> HintCollection:
        """
        Generate hints after adding research to a campaign.

        Args:
            campaign_id: Campaign ID
            campaign_name: Campaign name
            research_type: Type of research added
            task_count: Number of tasks in the campaign

        Returns:
            HintCollection with workflow guidance
        """
        if not self.enabled:
            return self._empty()

        if task_count == 0:
            return HintCollection(
                hints=[
                    Hint(
                        category=HintCategory.WORKFLOW,
                        message="Campaign research added. Continue planning or create tasks.",
                        tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                        context={
                            "campaign_id": campaign_id,
                            "research_type": research_type,
                        },
                    )
                ]
            )
        else:
            return HintCollection(
                hints=[
                    Hint(
                        category=HintCategory.PROGRESS,
                        message="Campaign research added. Continue planning or working on tasks.",
                        tool_call=None,  # Agent continues work
                        context={
                            "campaign_id": campaign_id,
                            "research_type": research_type,
                            "task_count": task_count,
                        },
                    )
                ]
            )

    # --- Bulk Operations Hints ---

    def post_campaign_create_with_tasks(
        self,
        campaign_id: str,
        campaign_name: str,
        task_count: int,
        tasks_with_criteria: int = 0,
    ) -> HintCollection:
        """
        Generate hints after creating campaign with tasks atomically.

        Args:
            campaign_id: Created campaign ID
            campaign_name: Campaign name
            task_count: Number of tasks created
            tasks_with_criteria: Number of tasks with acceptance criteria

        Returns:
            HintCollection with execution guidance
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        if task_count == 0:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=(
                        f"Campaign '{campaign_name}' created with no tasks. "
                        "Add tasks to begin."
                    ),
                    tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                    context={"campaign_id": campaign_id},
                )
            )
        elif tasks_with_criteria == task_count:
            # All tasks have criteria - ready for execution
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=(
                        f"Campaign '{campaign_name}' created with {task_count} tasks. "
                        "All tasks have acceptance criteria. Ready for execution."
                    ),
                    tool_call=(
                        f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')"
                    ),
                    context={
                        "campaign_id": campaign_id,
                        "task_count": task_count,
                        "with_criteria": tasks_with_criteria,
                    },
                )
            )
        else:
            # Some tasks need criteria
            missing = task_count - tasks_with_criteria
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=(
                        f"Campaign '{campaign_name}' created with {task_count} tasks. "
                        f"{missing} tasks need acceptance criteria."
                    ),
                    tool_call=(
                        f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')"
                    ),
                    context={
                        "campaign_id": campaign_id,
                        "task_count": task_count,
                        "with_criteria": tasks_with_criteria,
                        "without_criteria": missing,
                    },
                )
            )

        return HintCollection(hints=hints)

    # --- Parallel Execution Hints ---

    def actionable_tasks_hints(
        self,
        tasks: List[Dict[str, Any]],
        campaign_id: str,
        campaign_progress: Optional[Dict[str, Any]] = None,
    ) -> HintCollection:
        """
        Generate hints for parallel task execution.

        Args:
            tasks: List of actionable task data
            campaign_id: Campaign ID
            campaign_progress: Optional progress data

        Returns:
            HintCollection with parallel execution guidance
        """
        if not self.enabled:
            return self._empty()

        if not tasks or len(tasks) == 0:
            # Delegate to existing no-actionable logic
            return self.actionable_task_hints(
                task_data=None,
                campaign_id=campaign_id,
                campaign_progress=campaign_progress,
                no_actionable=True,
            )

        count = len(tasks)
        first_task_id = tasks[0].get("id", "")

        return HintCollection(
            hints=[
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"{count} actionable task{'s' if count > 1 else ''} available. "
                    "Claim by setting status to 'in-progress' before starting.",
                    tool_call=f"task_update(task_id='{first_task_id}', status='in-progress')",
                    context={
                        "campaign_id": campaign_id,
                        "actionable_count": count,
                        "task_ids": [t.get("id") for t in tasks],
                    },
                )
            ]
        )

    # --- Quality & Health Hints ---

    def task_quality_hints(
        self,
        completeness_info: TaskCompletenessInfo,
        context: str = "inspection",
    ) -> HintCollection:
        """
        Generate hints about task quality/completeness.

        Provides guidance on missing task elements like acceptance criteria,
        testing strategy, and research.

        Args:
            completeness_info: TaskCompletenessInfo with task quality data
            context: Hint context - controls filtering:
                - "inspection": Full quality hints (viewing task details)
                - "update": Only hint if task is in-progress
                - "actionable": Only warn about missing criteria (critical)

        Returns:
            HintCollection with quality improvement hints (max 2)
        """
        if not self.enabled:
            return self._empty()

        # Skip completed tasks - no quality hints needed
        if completeness_info.task_status == "done":
            return self._empty()

        # Context filtering
        if context == "update" and completeness_info.task_status != "in-progress":
            return self._empty()

        hints: List[Hint] = []
        task_id = completeness_info.task_id
        task_title = completeness_info.task_title

        # Priority 1: Missing acceptance criteria (critical)
        if not completeness_info.has_acceptance_criteria:
            hints.append(
                Hint(
                    category=HintCategory.QUALITY,
                    message=f"Task '{task_title}' has no acceptance criteria. "
                    "Define completion requirements.",
                    tool_call=f"task_acceptance_criteria_add(task_id='{task_id}', content='...')",
                    context={
                        "task_id": task_id,
                        "missing": "acceptance_criteria",
                    },
                )
            )

        # For actionable context, only show criteria warning
        if context == "actionable":
            return HintCollection(hints=hints[:1])

        # Priority 2: Missing testing strategy (only if criteria exist)
        if completeness_info.has_acceptance_criteria and not completeness_info.has_testing_strategy:
            hints.append(
                Hint(
                    category=HintCategory.QUALITY,
                    message=f"Task '{task_title}' has criteria but no testing strategy. "
                    "Plan verification steps.",
                    tool_call=f"task_testing_strategy_add(task_id='{task_id}', content='...')",
                    context={
                        "task_id": task_id,
                        "missing": "testing_strategy",
                    },
                )
            )

        # Priority 3: Missing research (only for inspection context)
        if context == "inspection" and not completeness_info.has_research:
            # Only add if we haven't hit max hints yet
            if len(hints) < 2:
                hints.append(
                    Hint(
                        category=HintCategory.QUALITY,
                        message=f"Task '{task_title}' has no research notes. "
                        "Consider documenting findings.",
                        tool_call=f"task_research_add(task_id='{task_id}', content='...')",
                        context={
                            "task_id": task_id,
                            "missing": "research",
                        },
                    )
                )

        # Noise reduction: max 2 quality hints
        return HintCollection(hints=hints[:2])

    def campaign_health_hints(
        self,
        health_info: CampaignHealthInfo,
        context: str = "overview",
    ) -> HintCollection:
        """
        Generate hints about campaign health and completeness.

        Provides guidance on tasks that need quality improvements
        and overall campaign readiness.

        Args:
            health_info: CampaignHealthInfo with campaign health data
            context: Hint context:
                - "overview": Include health score, general guidance
                - "validate": Actionable fixes for readiness issues

        Returns:
            HintCollection with campaign health hints
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []
        campaign_id = health_info.campaign_id

        # No tasks -> hint to add tasks
        if health_info.total_tasks == 0:
            hints.append(
                Hint(
                    category=HintCategory.QUALITY,
                    message="Campaign has no tasks. Add tasks to define the work.",
                    tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                    context={"campaign_id": campaign_id},
                )
            )
            return HintCollection(hints=hints)

        # Tasks without criteria
        if health_info.tasks_without_criteria > 0:
            count = health_info.tasks_without_criteria
            total = health_info.total_tasks
            first_task_id = health_info.first_task_without_criteria_id

            tool_call = None
            if first_task_id:
                tool_call = f"task_show(task_id='{first_task_id}')"

            hints.append(
                Hint(
                    category=HintCategory.QUALITY,
                    message=f"{count} of {total} tasks have no acceptance criteria.",
                    tool_call=tool_call,
                    context={
                        "campaign_id": campaign_id,
                        "tasks_without_criteria": count,
                        "first_task_id": first_task_id,
                    },
                )
            )

        # Tasks without testing (only if criteria are OK)
        if health_info.tasks_without_criteria == 0 and health_info.tasks_without_testing > 0:
            count = health_info.tasks_without_testing
            total = health_info.total_tasks
            first_task_id = health_info.first_task_without_testing_id

            tool_call = None
            if first_task_id:
                tool_call = f"task_show(task_id='{first_task_id}')"

            hints.append(
                Hint(
                    category=HintCategory.QUALITY,
                    message=f"{count} of {total} tasks have no testing strategy.",
                    tool_call=tool_call,
                    context={
                        "campaign_id": campaign_id,
                        "tasks_without_testing": count,
                        "first_task_id": first_task_id,
                    },
                )
            )

        # Include health score for overview context
        if context == "overview" and health_info.health_score < 100:
            hints.append(
                Hint(
                    category=HintCategory.PROGRESS,
                    message=f"Campaign health: {health_info.health_score}%. "
                    "Improve task definitions for better quality.",
                    tool_call=None,
                    context={
                        "campaign_id": campaign_id,
                        "health_score": health_info.health_score,
                    },
                )
            )

        return HintCollection(hints=hints)

    def campaign_setup_progress_hints(
        self,
        campaign_id: str,
        campaign_name: str,
        setup_stage: CampaignSetupStage,
        health_info: Optional[CampaignHealthInfo] = None,
    ) -> HintCollection:
        """
        Generate hints based on campaign setup stage.

        Provides stage-specific guidance to help users progress
        through campaign setup: create -> add tasks -> add criteria ->
        add testing -> execute -> complete.

        Args:
            campaign_id: Campaign UUID
            campaign_name: Campaign name for display
            setup_stage: Current CampaignSetupStage
            health_info: Optional CampaignHealthInfo for context

        Returns:
            HintCollection with setup progress hints
        """
        if not self.enabled:
            return self._empty()

        hints: List[Hint] = []

        # Stage-specific hints
        if setup_stage == CampaignSetupStage.CREATED:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message=f"Campaign '{campaign_name}' created. Next: Add tasks.",
                    tool_call=f"task_create(campaign_id='{campaign_id}', title='...')",
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                    },
                )
            )
        elif setup_stage == CampaignSetupStage.TASKS_ADDED:
            first_task_id = (
                health_info.first_task_without_criteria_id
                if health_info and health_info.first_task_without_criteria_id
                else None
            )
            tool_call = (
                f"task_show(task_id='{first_task_id}')"
                if first_task_id
                else f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')"
            )
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Tasks added. Next: Define acceptance criteria for each task.",
                    tool_call=tool_call,
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                        "first_task_id": first_task_id,
                    },
                )
            )
        elif setup_stage == CampaignSetupStage.CRITERIA_DEFINED:
            first_task_id = (
                health_info.first_task_without_testing_id
                if health_info and health_info.first_task_without_testing_id
                else None
            )
            tool_call = (
                f"task_show(task_id='{first_task_id}')"
                if first_task_id
                else f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')"
            )
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Criteria defined. Next: Add testing strategy for each task.",
                    tool_call=tool_call,
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                        "first_task_id": first_task_id,
                    },
                )
            )
        elif setup_stage == CampaignSetupStage.TESTING_PLANNED:
            hints.append(
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Campaign ready for execution. Start the first task.",
                    tool_call=f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')",
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                    },
                )
            )
        elif setup_stage == CampaignSetupStage.EXECUTING:
            hints.append(
                Hint(
                    category=HintCategory.PROGRESS,
                    message="Campaign in progress. Continue with the next actionable task.",
                    tool_call=f"campaign_get_next_actionable_task(campaign_id='{campaign_id}')",
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                    },
                )
            )
        elif setup_stage == CampaignSetupStage.COMPLETED:
            hints.append(
                Hint(
                    category=HintCategory.COMPLETION,
                    message=f"Campaign '{campaign_name}' complete! All tasks done.",
                    tool_call=f"campaign_update(campaign_id='{campaign_id}', status='completed')",
                    context={
                        "campaign_id": campaign_id,
                        "stage": setup_stage.value,
                    },
                )
            )

        return HintCollection(hints=hints)

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
