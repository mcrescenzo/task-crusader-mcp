"""Tests for the HintGenerator service."""

import pytest

from task_crusade_mcp.domain.entities.hint import Hint, HintCategory, HintCollection
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
