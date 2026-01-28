"""Tests for the HintGenerator service."""

import pytest

from task_crusade_mcp.domain.entities.hint import (
    CampaignHealthInfo,
    CampaignSetupStage,
    Hint,
    HintCategory,
    HintCollection,
    TaskCompletenessInfo,
)
from task_crusade_mcp.services.hint_generator import HintGenerator


class TestHintDataclass:
    """Tests for the Hint dataclass."""

    def test_hint_to_dict(self):
        """Test Hint.to_dict() serialization."""
        hint = Hint(
            category=HintCategory.WORKFLOW,
            message="Test message",
            tool_call="test_tool(id='123')",
            context={"key": "value"},
        )

        result = hint.to_dict()

        assert result == {
            "category": "workflow",
            "message": "Test message",
            "tool_call": "test_tool(id='123')",
            "context": {"key": "value"},
        }

    def test_hint_to_dict_without_optional_fields(self):
        """Test Hint.to_dict() with missing optional fields."""
        hint = Hint(
            category=HintCategory.PROGRESS,
            message="Progress update",
        )

        result = hint.to_dict()

        assert result == {
            "category": "progress",
            "message": "Progress update",
            "tool_call": None,
            "context": None,
        }


class TestHintCollection:
    """Tests for the HintCollection dataclass."""

    def test_to_list(self):
        """Test HintCollection.to_list() serialization."""
        collection = HintCollection(
            hints=[
                Hint(category=HintCategory.WORKFLOW, message="First"),
                Hint(category=HintCategory.PROGRESS, message="Second"),
            ]
        )

        result = collection.to_list()

        assert len(result) == 2
        assert result[0]["message"] == "First"
        assert result[1]["message"] == "Second"

    def test_get_primary_tool_call_workflow_priority(self):
        """Test that workflow hints are prioritized for primary tool call."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.PROGRESS,
                    message="Progress",
                    tool_call="progress_tool()",
                ),
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Workflow",
                    tool_call="workflow_tool()",
                ),
            ]
        )

        result = collection.get_primary_tool_call()

        assert result == "workflow_tool()"

    def test_get_primary_tool_call_fallback(self):
        """Test fallback to any hint with tool_call if no workflow hint."""
        collection = HintCollection(
            hints=[
                Hint(category=HintCategory.PROGRESS, message="No tool call"),
                Hint(
                    category=HintCategory.COORDINATION,
                    message="Has tool",
                    tool_call="coord_tool()",
                ),
            ]
        )

        result = collection.get_primary_tool_call()

        assert result == "coord_tool()"

    def test_get_primary_tool_call_none(self):
        """Test returns None when no hints have tool_call."""
        collection = HintCollection(
            hints=[
                Hint(category=HintCategory.PROGRESS, message="No tool"),
            ]
        )

        result = collection.get_primary_tool_call()

        assert result is None

    def test_is_empty(self):
        """Test is_empty()."""
        empty_collection = HintCollection(hints=[])
        non_empty_collection = HintCollection(
            hints=[Hint(category=HintCategory.WORKFLOW, message="Test")]
        )

        assert empty_collection.is_empty() is True
        assert non_empty_collection.is_empty() is False

    def test_len(self):
        """Test __len__()."""
        collection = HintCollection(
            hints=[
                Hint(category=HintCategory.WORKFLOW, message="One"),
                Hint(category=HintCategory.WORKFLOW, message="Two"),
            ]
        )

        assert len(collection) == 2


class TestHintGenerator:
    """Tests for the HintGenerator service."""

    @pytest.fixture
    def generator(self):
        """Create a HintGenerator instance."""
        return HintGenerator(enabled=True)

    @pytest.fixture
    def disabled_generator(self):
        """Create a disabled HintGenerator instance."""
        return HintGenerator(enabled=False)

    def test_disabled_generator_returns_empty(self, disabled_generator):
        """Test that disabled generator returns empty collections."""
        result = disabled_generator.post_campaign_create(
            campaign_id="test-id",
            campaign_name="Test Campaign",
        )

        assert result.is_empty()

    # --- Campaign Hint Tests ---

    def test_post_campaign_create(self, generator):
        """Test hints after campaign creation."""
        result = generator.post_campaign_create(
            campaign_id="camp-123",
            campaign_name="My Campaign",
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "My Campaign" in hint.message
        assert "created" in hint.message.lower()
        assert "task_create(campaign_id='camp-123'" in hint.tool_call
        assert hint.context["campaign_id"] == "camp-123"

    def test_post_campaign_progress_no_tasks(self, generator):
        """Test hints for campaign with no tasks."""
        result = generator.post_campaign_progress(
            campaign_id="camp-123",
            progress_data={
                "total_tasks": 0,
                "tasks_by_status": {},
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "no tasks" in hint.message.lower()
        assert "task_create" in hint.tool_call

    def test_post_campaign_progress_all_done(self, generator):
        """Test hints when all tasks are complete."""
        result = generator.post_campaign_progress(
            campaign_id="camp-123",
            progress_data={
                "total_tasks": 5,
                "completion_rate": 100.0,
                "tasks_by_status": {
                    "done": 5,
                    "pending": 0,
                    "in-progress": 0,
                    "blocked": 0,
                },
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COMPLETION
        assert "complete" in hint.message.lower()
        assert "campaign_update" in hint.tool_call

    def test_post_campaign_progress_in_progress(self, generator):
        """Test hints when campaign has active tasks."""
        result = generator.post_campaign_progress(
            campaign_id="camp-123",
            progress_data={
                "total_tasks": 10,
                "completion_rate": 50.0,
                "tasks_by_status": {
                    "done": 5,
                    "pending": 3,
                    "in-progress": 1,
                    "blocked": 1,
                },
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "5/10" in hint.message
        assert "50%" in hint.message
        assert "campaign_get_next_actionable_task" in hint.tool_call

    # --- Task Hint Tests ---

    def test_post_task_create_no_criteria(self, generator):
        """Test hints for task created without acceptance criteria."""
        result = generator.post_task_create(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            has_acceptance_criteria=False,
            criteria_count=0,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "acceptance criteria" in hint.message.lower()
        assert "task_acceptance_criteria_add(task_id='task-456'" in hint.tool_call

    def test_post_task_create_with_criteria(self, generator):
        """Test hints for task created with acceptance criteria."""
        result = generator.post_task_create(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            has_acceptance_criteria=True,
            criteria_count=3,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "3 criteria" in hint.message
        assert "ready" in hint.message.lower()
        assert "task_update(task_id='task-456', status='in-progress')" in hint.tool_call

    def test_post_task_status_change_to_in_progress(self, generator):
        """Test hints when task is started."""
        result = generator.post_task_status_change(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            old_status="pending",
            new_status="in-progress",
            criteria_count=3,
            unmet_criteria_count=3,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "started" in hint.message.lower()
        assert "3 criteria" in hint.message
        # No tool_call because agent should implement the task
        assert hint.tool_call is None

    def test_post_task_status_change_to_blocked(self, generator):
        """Test hints when task becomes blocked."""
        result = generator.post_task_status_change(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            old_status="pending",
            new_status="blocked",
            criteria_count=3,
            unmet_criteria_count=3,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COORDINATION
        assert "blocked" in hint.message.lower()
        assert "task_show" in hint.tool_call

    def test_post_task_complete_more_tasks(self, generator):
        """Test hints when task completes but more tasks remain."""
        result = generator.post_task_complete(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            campaign_progress={
                "total_tasks": 10,
                "completion_rate": 60.0,
                "tasks_by_status": {
                    "done": 6,
                    "pending": 3,
                    "in-progress": 0,
                    "blocked": 1,
                },
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "6/10" in hint.message
        assert "60%" in hint.message
        assert "campaign_get_next_actionable_task" in hint.tool_call

    def test_post_task_complete_campaign_done(self, generator):
        """Test hints when last task completes campaign."""
        result = generator.post_task_complete(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            campaign_progress={
                "total_tasks": 5,
                "completion_rate": 100.0,
                "tasks_by_status": {
                    "done": 5,
                    "pending": 0,
                    "in-progress": 0,
                    "blocked": 0,
                },
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COMPLETION
        assert "complete" in hint.message.lower()
        assert "campaign_update" in hint.tool_call
        assert "completed" in hint.tool_call

    # --- Actionable Task Hint Tests ---

    def test_actionable_task_hints_found(self, generator):
        """Test hints when actionable task is found."""
        result = generator.actionable_task_hints(
            task_data={
                "id": "task-456",
                "title": "Next Task",
                "acceptance_criteria_details": [
                    {"id": "crit-1", "content": "Test", "is_met": False},
                    {"id": "crit-2", "content": "Test2", "is_met": False},
                ],
            },
            campaign_id="camp-123",
            campaign_progress=None,
            no_actionable=False,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "Next Task" in hint.message
        assert "2 criteria" in hint.message
        assert "task_update(task_id='task-456', status='in-progress')" in hint.tool_call
        assert "crit-1" in hint.context["criteria_ids"]
        assert "crit-2" in hint.context["criteria_ids"]

    def test_actionable_task_hints_none_blocked(self, generator):
        """Test hints when no actionable task due to blocking."""
        result = generator.actionable_task_hints(
            task_data=None,
            campaign_id="camp-123",
            campaign_progress={
                "tasks_by_status": {
                    "pending": 0,
                    "blocked": 3,
                    "done": 5,
                },
            },
            no_actionable=True,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COORDINATION
        assert "blocked" in hint.message.lower()
        assert "3" in hint.message
        assert "task_list" in hint.tool_call
        assert "blocked" in hint.tool_call

    def test_actionable_task_hints_campaign_complete(self, generator):
        """Test hints when no actionable because campaign is complete."""
        result = generator.actionable_task_hints(
            task_data=None,
            campaign_id="camp-123",
            campaign_progress={
                "tasks_by_status": {
                    "pending": 0,
                    "blocked": 0,
                    "done": 5,
                },
            },
            no_actionable=True,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COMPLETION
        assert "complete" in hint.message.lower()
        assert "campaign_update" in hint.tool_call

    # --- Criteria Hint Tests ---

    def test_post_criteria_met_partial(self, generator):
        """Test hints when some criteria are met."""
        result = generator.post_criteria_met(
            task_id="task-456",
            task_title="My Task",
            criteria_id="crit-1",
            met_count=2,
            total_count=5,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "2/5" in hint.message
        assert "3 remaining" in hint.message
        # No tool_call because agent should continue implementing
        assert hint.tool_call is None

    def test_post_criteria_met_all(self, generator):
        """Test hints when all criteria are met."""
        result = generator.post_criteria_met(
            task_id="task-456",
            task_title="My Task",
            criteria_id="crit-5",
            met_count=5,
            total_count=5,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COMPLETION
        assert "all" in hint.message.lower()
        assert "5 criteria" in hint.message
        assert "task_complete(task_id='task-456')" in hint.tool_call

    def test_post_criteria_unmet(self, generator):
        """Test hints when criteria is unmarked."""
        result = generator.post_criteria_unmet(
            task_id="task-456",
            task_title="My Task",
            criteria_id="crit-3",
            met_count=2,
            total_count=5,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "2/5" in hint.message
        assert "3 remaining" in hint.message

    # --- Utility Method Tests ---

    def test_format_for_response_empty(self, generator):
        """Test format_for_response with empty collection."""
        empty = HintCollection(hints=[])

        result = generator.format_for_response(empty)

        assert result == {}

    def test_format_for_response_with_hints(self, generator):
        """Test format_for_response with hints."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Test message",
                    tool_call="test_tool()",
                )
            ]
        )

        result = generator.format_for_response(collection)

        assert "hints" in result
        assert len(result["hints"]) == 1
        assert "next_action" in result
        assert result["next_action"] == "test_tool()"

    def test_format_for_response_no_tool_call(self, generator):
        """Test format_for_response when no tool_call present."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.PROGRESS,
                    message="Progress update",
                )
            ]
        )

        result = generator.format_for_response(collection)

        assert "hints" in result
        assert "next_action" not in result

    # --- Task Memory Operations Hint Tests ---

    def test_post_acceptance_criteria_add(self, generator):
        """Test hints after adding acceptance criteria."""
        result = generator.post_acceptance_criteria_add(
            task_id="task-456",
            task_title="My Task",
            criteria_count=3,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "3 total" in hint.message
        assert "My Task" in hint.message
        assert "task_update(task_id='task-456', status='in-progress')" in hint.tool_call

    def test_post_research_add(self, generator):
        """Test hints after adding research - no tool call expected."""
        result = generator.post_research_add(
            task_id="task-456",
            task_title="My Task",
            research_type="findings",
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "My Task" in hint.message
        assert "Continue implementing" in hint.message
        # No tool call - agent should continue work
        assert hint.tool_call is None

    def test_post_implementation_note_add_with_unmet_criteria(self, generator):
        """Test hints after adding note with unmet criteria."""
        result = generator.post_implementation_note_add(
            task_id="task-456",
            task_title="My Task",
            unmet_criteria=[
                {"id": "crit-1", "content": "First criterion"},
                {"id": "crit-2", "content": "Second criterion"},
            ],
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "My Task" in hint.message
        assert "Mark criteria" in hint.message
        assert "task_acceptance_criteria_mark_met(criteria_id='crit-1')" in hint.tool_call
        assert hint.context["unmet_count"] == 2

    def test_post_implementation_note_add_no_unmet_criteria(self, generator):
        """Test hints after adding note with no unmet criteria."""
        result = generator.post_implementation_note_add(
            task_id="task-456",
            task_title="My Task",
            unmet_criteria=[],
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "My Task" in hint.message
        assert "Continue implementing" in hint.message
        # No tool call when no unmet criteria
        assert hint.tool_call is None

    def test_post_testing_step_add(self, generator):
        """Test hints after adding a testing step."""
        result = generator.post_testing_step_add(
            task_id="task-456",
            task_title="My Task",
            step_type="verify",
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "My Task" in hint.message
        assert "Run tests" in hint.message
        # No tool call - agent should run tests
        assert hint.tool_call is None
        assert hint.context["step_type"] == "verify"

    # --- Campaign Research Hint Tests ---

    def test_post_campaign_research_add_no_tasks(self, generator):
        """Test hints after campaign research when no tasks exist."""
        result = generator.post_campaign_research_add(
            campaign_id="camp-123",
            campaign_name="My Campaign",
            research_type="analysis",
            task_count=0,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "research added" in hint.message.lower()
        assert "task_create(campaign_id='camp-123'" in hint.tool_call

    def test_post_campaign_research_add_has_tasks(self, generator):
        """Test hints after campaign research when tasks exist."""
        result = generator.post_campaign_research_add(
            campaign_id="camp-123",
            campaign_name="My Campaign",
            research_type="strategy",
            task_count=5,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "research added" in hint.message.lower()
        # No task_create suggested when tasks already exist
        assert hint.tool_call is None

    # --- Status Change with Blocking Info Tests ---

    def test_post_task_status_change_blocked_with_dependencies(self, generator):
        """Test hints when task becomes blocked with dependency info."""
        result = generator.post_task_status_change(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            old_status="pending",
            new_status="blocked",
            criteria_count=0,
            unmet_criteria_count=0,
            blocking_tasks=[
                {"id": "task-100", "title": "First Blocker"},
                {"id": "task-101", "title": "Second Blocker"},
            ],
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COORDINATION
        assert "First Blocker" in hint.message
        assert "Second Blocker" in hint.message
        assert "task_show(task_id='task-100')" in hint.tool_call

    def test_post_task_status_change_blocked_many_dependencies(self, generator):
        """Test hints when task blocked by many dependencies (truncation)."""
        result = generator.post_task_status_change(
            task_id="task-456",
            task_title="My Task",
            campaign_id="camp-123",
            old_status="pending",
            new_status="blocked",
            criteria_count=0,
            unmet_criteria_count=0,
            blocking_tasks=[
                {"id": "task-100", "title": "Blocker 1"},
                {"id": "task-101", "title": "Blocker 2"},
                {"id": "task-102", "title": "Blocker 3"},
                {"id": "task-103", "title": "Blocker 4"},
                {"id": "task-104", "title": "Blocker 5"},
            ],
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COORDINATION
        assert "Blocker 1" in hint.message
        assert "Blocker 2" in hint.message
        assert "Blocker 3" in hint.message
        assert "(+2 more)" in hint.message

    # --- Parallel Execution Hint Tests ---

    def test_actionable_tasks_hints_multiple(self, generator):
        """Test hints for multiple actionable tasks."""
        result = generator.actionable_tasks_hints(
            tasks=[
                {"id": "task-1", "title": "Task One"},
                {"id": "task-2", "title": "Task Two"},
                {"id": "task-3", "title": "Task Three"},
            ],
            campaign_id="camp-123",
            campaign_progress=None,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "3 actionable tasks" in hint.message
        assert "in-progress" in hint.message.lower()
        assert "task_update(task_id='task-1', status='in-progress')" in hint.tool_call
        assert hint.context["actionable_count"] == 3

    def test_actionable_tasks_hints_single(self, generator):
        """Test hints for single actionable task (no plural 's')."""
        result = generator.actionable_tasks_hints(
            tasks=[{"id": "task-1", "title": "Task One"}],
            campaign_id="camp-123",
            campaign_progress=None,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert "1 actionable task available" in hint.message
        assert "tasks" not in hint.message  # Should be "task" not "tasks"

    def test_actionable_tasks_hints_empty(self, generator):
        """Test hints for empty actionable tasks delegates to no-actionable logic."""
        result = generator.actionable_tasks_hints(
            tasks=[],
            campaign_id="camp-123",
            campaign_progress={
                "tasks_by_status": {
                    "pending": 0,
                    "blocked": 2,
                    "done": 3,
                },
            },
        )

        assert len(result) == 1
        hint = result.hints[0]
        # Should use the no-actionable hint logic
        assert hint.category == HintCategory.COORDINATION
        assert "blocked" in hint.message.lower()

    # --- Disabled Generator Tests for New Methods ---

    def test_post_acceptance_criteria_add_disabled(self, disabled_generator):
        """Test disabled generator returns empty for acceptance criteria add."""
        result = disabled_generator.post_acceptance_criteria_add(
            task_id="task-456",
            task_title="My Task",
            criteria_count=3,
        )
        assert result.is_empty()

    def test_post_research_add_disabled(self, disabled_generator):
        """Test disabled generator returns empty for research add."""
        result = disabled_generator.post_research_add(
            task_id="task-456",
            task_title="My Task",
            research_type="findings",
        )
        assert result.is_empty()

    def test_post_implementation_note_add_disabled(self, disabled_generator):
        """Test disabled generator returns empty for implementation note add."""
        result = disabled_generator.post_implementation_note_add(
            task_id="task-456",
            task_title="My Task",
            unmet_criteria=[{"id": "crit-1"}],
        )
        assert result.is_empty()

    def test_post_testing_step_add_disabled(self, disabled_generator):
        """Test disabled generator returns empty for testing step add."""
        result = disabled_generator.post_testing_step_add(
            task_id="task-456",
            task_title="My Task",
            step_type="verify",
        )
        assert result.is_empty()

    def test_post_campaign_research_add_disabled(self, disabled_generator):
        """Test disabled generator returns empty for campaign research add."""
        result = disabled_generator.post_campaign_research_add(
            campaign_id="camp-123",
            campaign_name="My Campaign",
            research_type="analysis",
            task_count=0,
        )
        assert result.is_empty()

    def test_actionable_tasks_hints_disabled(self, disabled_generator):
        """Test disabled generator returns empty for actionable tasks hints."""
        result = disabled_generator.actionable_tasks_hints(
            tasks=[{"id": "task-1"}],
            campaign_id="camp-123",
            campaign_progress=None,
        )
        assert result.is_empty()


class TestTaskQualityHints:
    """Tests for task_quality_hints method."""

    @pytest.fixture
    def generator(self):
        """Create a HintGenerator instance."""
        return HintGenerator(enabled=True)

    @pytest.fixture
    def disabled_generator(self):
        """Create a disabled HintGenerator instance."""
        return HintGenerator(enabled=False)

    def test_task_quality_hints_disabled(self, disabled_generator):
        """Test disabled generator returns empty for task quality hints."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = disabled_generator.task_quality_hints(info)
        assert result.is_empty()

    def test_task_quality_hints_completed_task_no_hints(self, generator):
        """Test that completed tasks get no quality hints."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="done",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = generator.task_quality_hints(info)
        assert result.is_empty()

    def test_task_quality_hints_missing_criteria(self, generator):
        """Test hints when task is missing acceptance criteria."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=True,
            testing_steps_count=2,
            has_research=True,
        )
        result = generator.task_quality_hints(info)

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "no acceptance criteria" in hint.message
        assert "task_acceptance_criteria_add" in hint.tool_call
        assert hint.context["missing"] == "acceptance_criteria"

    def test_task_quality_hints_missing_testing(self, generator):
        """Test hints when task has criteria but missing testing strategy."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=True,
        )
        result = generator.task_quality_hints(info)

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "no testing strategy" in hint.message
        assert "task_testing_strategy_add" in hint.tool_call
        assert hint.context["missing"] == "testing_strategy"

    def test_task_quality_hints_missing_research_inspection(self, generator):
        """Test hints for missing research in inspection context."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=True,
            testing_steps_count=2,
            has_research=False,
        )
        result = generator.task_quality_hints(info, context="inspection")

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "no research" in hint.message
        assert "task_research_add" in hint.tool_call
        assert hint.context["missing"] == "research"

    def test_task_quality_hints_multiple_missing_max_two(self, generator):
        """Test that max 2 quality hints are returned."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = generator.task_quality_hints(info, context="inspection")

        # Should get max 2 hints even though 3 things are missing
        assert len(result) <= 2
        # First should be criteria (highest priority)
        assert result.hints[0].context["missing"] == "acceptance_criteria"

    def test_task_quality_hints_actionable_context_only_criteria(self, generator):
        """Test actionable context only shows criteria warnings."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = generator.task_quality_hints(info, context="actionable")

        # Only 1 hint for criteria in actionable context
        assert len(result) == 1
        assert result.hints[0].context["missing"] == "acceptance_criteria"

    def test_task_quality_hints_update_context_only_in_progress(self, generator):
        """Test update context only hints for in-progress tasks."""
        # Pending task - no hints in update context
        info_pending = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = generator.task_quality_hints(info_pending, context="update")
        assert result.is_empty()

        # In-progress task - hints in update context
        info_in_progress = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="in-progress",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        result = generator.task_quality_hints(info_in_progress, context="update")
        assert not result.is_empty()

    def test_task_quality_hints_complete_task_no_hints(self, generator):
        """Test that fully complete task gets no quality hints."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test Task",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=True,
            testing_steps_count=2,
            has_research=True,
        )
        result = generator.task_quality_hints(info, context="inspection")

        assert result.is_empty()


class TestCampaignHealthHints:
    """Tests for campaign_health_hints method."""

    @pytest.fixture
    def generator(self):
        """Create a HintGenerator instance."""
        return HintGenerator(enabled=True)

    @pytest.fixture
    def disabled_generator(self):
        """Create a disabled HintGenerator instance."""
        return HintGenerator(enabled=False)

    def test_campaign_health_hints_disabled(self, disabled_generator):
        """Test disabled generator returns empty for campaign health hints."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=0,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=0,
        )
        result = disabled_generator.campaign_health_hints(info)
        assert result.is_empty()

    def test_campaign_health_hints_no_tasks(self, generator):
        """Test hints when campaign has no tasks."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=0,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=0,
        )
        result = generator.campaign_health_hints(info)

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "no tasks" in hint.message.lower()
        assert "task_create" in hint.tool_call

    def test_campaign_health_hints_tasks_without_criteria(self, generator):
        """Test hints when tasks are missing criteria."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=5,
            tasks_without_criteria=3,
            tasks_without_testing=4,
            first_task_without_criteria_id="task-first",
            first_task_without_testing_id="task-first-test",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        result = generator.campaign_health_hints(info, context="overview")

        # Should have criteria hint
        criteria_hints = [h for h in result.hints if "criteria" in h.message.lower()]
        assert len(criteria_hints) >= 1
        hint = criteria_hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "3 of 5" in hint.message
        assert "task_show(task_id='task-first')" in hint.tool_call

    def test_campaign_health_hints_tasks_without_testing_only(self, generator):
        """Test hints when all have criteria but some missing testing."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=5,
            tasks_without_criteria=0,
            tasks_without_testing=2,
            first_task_without_criteria_id=None,
            first_task_without_testing_id="task-first-test",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        result = generator.campaign_health_hints(info, context="overview")

        # Should have testing hint (no criteria hint since all have criteria)
        testing_hints = [h for h in result.hints if "testing" in h.message.lower()]
        assert len(testing_hints) >= 1
        hint = testing_hints[0]
        assert hint.category == HintCategory.QUALITY
        assert "2 of 5" in hint.message
        assert "task_show(task_id='task-first-test')" in hint.tool_call

    def test_campaign_health_hints_health_score_overview(self, generator):
        """Test health score hint in overview context."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=5,
            tasks_without_criteria=2,
            tasks_without_testing=3,
            first_task_without_criteria_id="task-1",
            first_task_without_testing_id="task-2",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        result = generator.campaign_health_hints(info, context="overview")

        # Should include health score hint
        health_hints = [h for h in result.hints if "health" in h.message.lower()]
        assert len(health_hints) >= 1
        # Health score should be included in context
        assert health_hints[0].context.get("health_score") is not None

    def test_campaign_health_hints_healthy_campaign(self, generator):
        """Test no quality hints for healthy campaign."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=5,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=2,
            tasks_in_progress=1,
            tasks_blocked=0,
            tasks_pending=2,
        )
        result = generator.campaign_health_hints(info, context="overview")

        # Should not have quality hints (only maybe progress)
        quality_hints = [h for h in result.hints if h.category == HintCategory.QUALITY]
        assert len(quality_hints) == 0


class TestCampaignSetupProgressHints:
    """Tests for campaign_setup_progress_hints method."""

    @pytest.fixture
    def generator(self):
        """Create a HintGenerator instance."""
        return HintGenerator(enabled=True)

    @pytest.fixture
    def disabled_generator(self):
        """Create a disabled HintGenerator instance."""
        return HintGenerator(enabled=False)

    def test_campaign_setup_progress_hints_disabled(self, disabled_generator):
        """Test disabled generator returns empty for setup progress hints."""
        result = disabled_generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.CREATED,
        )
        assert result.is_empty()

    def test_setup_stage_created(self, generator):
        """Test hints for CREATED stage."""
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.CREATED,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "created" in hint.message.lower()
        assert "Add tasks" in hint.message
        assert "task_create(campaign_id='camp-1'" in hint.tool_call
        assert hint.context["stage"] == "created"

    def test_setup_stage_tasks_added(self, generator):
        """Test hints for TASKS_ADDED stage."""
        health_info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=3,
            tasks_without_criteria=3,
            tasks_without_testing=3,
            first_task_without_criteria_id="task-first",
            first_task_without_testing_id="task-first",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=3,
        )
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.TASKS_ADDED,
            health_info=health_info,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "acceptance criteria" in hint.message.lower()
        assert "task_show(task_id='task-first')" in hint.tool_call
        assert hint.context["stage"] == "tasks_added"

    def test_setup_stage_criteria_defined(self, generator):
        """Test hints for CRITERIA_DEFINED stage."""
        health_info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            total_tasks=3,
            tasks_without_criteria=0,
            tasks_without_testing=3,
            first_task_without_criteria_id=None,
            first_task_without_testing_id="task-first-test",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=3,
        )
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.CRITERIA_DEFINED,
            health_info=health_info,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "testing strategy" in hint.message.lower()
        assert "task_show(task_id='task-first-test')" in hint.tool_call
        assert hint.context["stage"] == "criteria_defined"

    def test_setup_stage_testing_planned(self, generator):
        """Test hints for TESTING_PLANNED stage."""
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.TESTING_PLANNED,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.WORKFLOW
        assert "ready for execution" in hint.message.lower()
        assert "campaign_get_next_actionable_task(campaign_id='camp-1')" in hint.tool_call
        assert hint.context["stage"] == "testing_planned"

    def test_setup_stage_executing(self, generator):
        """Test hints for EXECUTING stage."""
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.EXECUTING,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.PROGRESS
        assert "in progress" in hint.message.lower()
        assert "campaign_get_next_actionable_task(campaign_id='camp-1')" in hint.tool_call
        assert hint.context["stage"] == "executing"

    def test_setup_stage_completed(self, generator):
        """Test hints for COMPLETED stage."""
        result = generator.campaign_setup_progress_hints(
            campaign_id="camp-1",
            campaign_name="Test Campaign",
            setup_stage=CampaignSetupStage.COMPLETED,
        )

        assert len(result) == 1
        hint = result.hints[0]
        assert hint.category == HintCategory.COMPLETION
        assert "complete" in hint.message.lower()
        assert "campaign_update(campaign_id='camp-1', status='completed')" in hint.tool_call
        assert hint.context["stage"] == "completed"


class TestHintCollectionPriorityWithQuality:
    """Tests for HintCollection priority ordering including QUALITY category."""

    def test_quality_hints_priority_after_workflow(self):
        """Test that QUALITY hints are prioritized after WORKFLOW."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.PROGRESS,
                    message="Progress",
                    tool_call="progress_tool()",
                ),
                Hint(
                    category=HintCategory.QUALITY,
                    message="Quality",
                    tool_call="quality_tool()",
                ),
                Hint(
                    category=HintCategory.COORDINATION,
                    message="Coordination",
                    tool_call="coord_tool()",
                ),
            ]
        )

        result = collection.get_primary_tool_call()
        assert result == "quality_tool()"

    def test_workflow_beats_quality(self):
        """Test that WORKFLOW hints beat QUALITY hints."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.QUALITY,
                    message="Quality",
                    tool_call="quality_tool()",
                ),
                Hint(
                    category=HintCategory.WORKFLOW,
                    message="Workflow",
                    tool_call="workflow_tool()",
                ),
            ]
        )

        result = collection.get_primary_tool_call()
        assert result == "workflow_tool()"

    def test_quality_beats_coordination(self):
        """Test that QUALITY hints beat COORDINATION hints."""
        collection = HintCollection(
            hints=[
                Hint(
                    category=HintCategory.COORDINATION,
                    message="Coordination",
                    tool_call="coord_tool()",
                ),
                Hint(
                    category=HintCategory.QUALITY,
                    message="Quality",
                    tool_call="quality_tool()",
                ),
            ]
        )

        result = collection.get_primary_tool_call()
        assert result == "quality_tool()"


class TestTaskCompletenessInfoDataclass:
    """Tests for TaskCompletenessInfo dataclass."""

    def test_missing_items_none(self):
        """Test missing_items when task is complete."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=True,
            testing_steps_count=2,
            has_research=True,
        )
        assert info.missing_items == []

    def test_missing_items_all(self):
        """Test missing_items when everything is missing."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test",
            task_status="pending",
            has_acceptance_criteria=False,
            criteria_count=0,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=False,
        )
        assert info.missing_items == ["acceptance_criteria", "testing_strategy", "research"]

    def test_is_complete_true(self):
        """Test is_complete when task has criteria and testing."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=True,
            testing_steps_count=2,
            has_research=False,  # Research not required
        )
        assert info.is_complete is True

    def test_is_complete_false(self):
        """Test is_complete when missing criteria or testing."""
        info = TaskCompletenessInfo(
            task_id="task-1",
            task_title="Test",
            task_status="pending",
            has_acceptance_criteria=True,
            criteria_count=3,
            has_testing_strategy=False,
            testing_steps_count=0,
            has_research=True,
        )
        assert info.is_complete is False


class TestCampaignHealthInfoDataclass:
    """Tests for CampaignHealthInfo dataclass."""

    def test_is_ready_for_execution_true(self):
        """Test is_ready_for_execution when all tasks have criteria."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=5,
            tasks_without_criteria=0,
            tasks_without_testing=2,
            first_task_without_criteria_id=None,
            first_task_without_testing_id="task-1",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        assert info.is_ready_for_execution is True

    def test_is_ready_for_execution_false_no_tasks(self):
        """Test is_ready_for_execution when no tasks."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=0,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=0,
        )
        assert info.is_ready_for_execution is False

    def test_is_ready_for_execution_false_missing_criteria(self):
        """Test is_ready_for_execution when some tasks missing criteria."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=5,
            tasks_without_criteria=2,
            tasks_without_testing=3,
            first_task_without_criteria_id="task-1",
            first_task_without_testing_id="task-1",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        assert info.is_ready_for_execution is False

    def test_health_score_perfect(self):
        """Test health_score when all tasks have criteria and testing."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=5,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        assert info.health_score == 100.0

    def test_health_score_partial(self):
        """Test health_score with partial coverage."""
        # 3 of 5 have criteria (60% of 60 = 36)
        # 2 of 5 have testing (40% of 40 = 16)
        # Total = 52
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=5,
            tasks_without_criteria=2,  # 3 have criteria
            tasks_without_testing=3,  # 2 have testing
            first_task_without_criteria_id="task-1",
            first_task_without_testing_id="task-1",
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=5,
        )
        assert info.health_score == 52.0

    def test_health_score_no_tasks(self):
        """Test health_score when no tasks."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=0,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=0,
        )
        assert info.health_score == 0.0

    def test_completion_rate(self):
        """Test completion_rate calculation."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=5,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=3,
            tasks_in_progress=1,
            tasks_blocked=0,
            tasks_pending=1,
        )
        assert info.completion_rate == 60.0

    def test_completion_rate_no_tasks(self):
        """Test completion_rate when no tasks."""
        info = CampaignHealthInfo(
            campaign_id="camp-1",
            campaign_name="Test",
            total_tasks=0,
            tasks_without_criteria=0,
            tasks_without_testing=0,
            first_task_without_criteria_id=None,
            first_task_without_testing_id=None,
            tasks_complete=0,
            tasks_in_progress=0,
            tasks_blocked=0,
            tasks_pending=0,
        )
        assert info.completion_rate == 0.0
