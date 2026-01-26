"""Integration tests for task workflows."""

import pytest
import yaml

from task_crusade_mcp.server.service_executor import ServiceExecutor


@pytest.fixture
def service_executor():
    """Create a service executor with test database."""
    executor = ServiceExecutor()
    yield executor
    executor.close()


@pytest.fixture
async def campaign_with_task(service_executor):
    """Create a campaign and task for testing."""
    # Create campaign
    campaign_result = await service_executor.execute_tool(
        "campaign_create",
        {"name": "Test Campaign"},
    )
    campaign_data = yaml.safe_load(campaign_result)
    campaign_id = campaign_data["data"]["id"]

    # Create task
    task_result = await service_executor.execute_tool(
        "task_create",
        {
            "title": "Test Task",
            "campaign_id": campaign_id,
        },
    )
    task_data = yaml.safe_load(task_result)
    task_id = task_data["data"]["id"]

    return {"campaign_id": campaign_id, "task_id": task_id}


class TestTaskWorkflows:
    """Test end-to-end task workflows."""

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, service_executor):
        """Test complete task lifecycle from creation to completion."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Lifecycle Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create task with all details
        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Complete Feature Implementation",
                "campaign_id": campaign_id,
                "description": "Implement new user authentication feature",
                "priority": "high",
                "type": "code",
                "acceptance_criteria": [
                    "User can log in with email and password",
                    "JWT tokens are issued on successful login",
                    "Failed login attempts are logged",
                ],
            },
        )
        task_data = yaml.safe_load(task_result)
        assert task_data["success"] is True
        task_id = task_data["data"]["id"]
        assert task_data["data"]["status"] == "pending"

        # Add research
        research_result = await service_executor.execute_tool(
            "task_research_add",
            {
                "task_id": task_id,
                "content": "JWT library: jsonwebtoken npm package",
                "research_type": "approaches",
            },
        )
        research_data = yaml.safe_load(research_result)
        assert research_data["success"] is True

        # Update task to in-progress
        update_result = await service_executor.execute_tool(
            "task_update",
            {
                "task_id": task_id,
                "status": "in-progress",
            },
        )
        update_data = yaml.safe_load(update_result)
        assert update_data["success"] is True
        assert update_data["data"]["status"] == "in-progress"

        # Add implementation notes
        note1_result = await service_executor.execute_tool(
            "task_implementation_notes_add",
            {
                "task_id": task_id,
                "content": "Started with user model and authentication middleware",
            },
        )
        note1_data = yaml.safe_load(note1_result)
        assert note1_data["success"] is True

        note2_result = await service_executor.execute_tool(
            "task_implementation_notes_add",
            {
                "task_id": task_id,
                "content": "Implemented JWT token generation and validation",
            },
        )
        note2_data = yaml.safe_load(note2_result)
        assert note2_data["success"] is True

        # Add testing steps
        test_steps = [
            {"content": "Set up test database", "step_type": "setup"},
            {"content": "Create test user account", "step_type": "setup"},
            {"content": "POST to /api/login with valid credentials", "step_type": "trigger"},
            {"content": "Verify JWT token is returned", "step_type": "verify"},
            {"content": "Verify token contains user ID", "step_type": "verify"},
            {"content": "Clean up test data", "step_type": "cleanup"},
        ]

        for step in test_steps:
            step_result = await service_executor.execute_tool(
                "task_testing_step_add",
                {
                    "task_id": task_id,
                    "content": step["content"],
                    "step_type": step["step_type"],
                },
            )
            step_data = yaml.safe_load(step_result)
            assert step_data["success"] is True

        # View complete task with all details
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert show_data["success"] is True
        task_details = show_data["data"]
        assert len(task_details["acceptance_criteria_details"]) == 3
        assert len(task_details["research"]) == 1
        assert len(task_details["implementation_notes"]) == 2
        assert len(task_details["testing_steps"]) == 6

        # Mark all acceptance criteria as met
        for criterion in task_data["data"]["acceptance_criteria_details"]:
            criteria_result = await service_executor.execute_tool(
                "task_acceptance_criteria_mark_met",
                {"criteria_id": criterion["id"]},
            )
            criteria_data = yaml.safe_load(criteria_result)
            assert criteria_data["success"] is True

        # Complete the task
        complete_result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task_id},
        )
        complete_data = yaml.safe_load(complete_result)
        assert complete_data["success"] is True
        assert complete_data["data"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_task_dependency_chain(self, service_executor):
        """Test tasks with dependency chains."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Dependency Chain Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create Task A (no dependencies)
        task_a_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task A - Foundation",
                "campaign_id": campaign_id,
            },
        )
        task_a_data = yaml.safe_load(task_a_result)
        task_a_id = task_a_data["data"]["id"]

        # Create Task B (depends on A)
        task_b_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task B - Builds on A",
                "campaign_id": campaign_id,
                "dependencies": [task_a_id],
            },
        )
        task_b_data = yaml.safe_load(task_b_result)
        task_b_id = task_b_data["data"]["id"]

        # Create Task C (depends on B)
        task_c_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task C - Builds on B",
                "campaign_id": campaign_id,
                "dependencies": [task_b_id],
            },
        )
        task_c_data = yaml.safe_load(task_c_result)
        task_c_id = task_c_data["data"]["id"]

        # Only Task A should be actionable
        next_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next_data = yaml.safe_load(next_result)
        assert next_data["success"] is True
        assert next_data["data"]["task"]["id"] == task_a_id

        # Complete Task A
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task_a_id, "status": "done"},
        )

        # Now Task B should be actionable
        next2_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next2_data = yaml.safe_load(next2_result)
        assert next2_data["success"] is True
        assert next2_data["data"]["task"]["id"] == task_b_id

        # Complete Task B
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task_b_id, "status": "done"},
        )

        # Now Task C should be actionable
        next3_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next3_data = yaml.safe_load(next3_result)
        assert next3_data["success"] is True
        assert next3_data["data"]["task"]["id"] == task_c_id

    @pytest.mark.asyncio
    async def test_task_with_multiple_dependencies(self, service_executor):
        """Test task with multiple dependencies (AND condition)."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Multiple Dependencies"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create Task 1 and Task 2 (independent)
        task1_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task 1 - Backend API",
                "campaign_id": campaign_id,
            },
        )
        task1_data = yaml.safe_load(task1_result)
        task1_id = task1_data["data"]["id"]

        task2_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task 2 - Frontend UI",
                "campaign_id": campaign_id,
            },
        )
        task2_data = yaml.safe_load(task2_result)
        task2_id = task2_data["data"]["id"]

        # Create Task 3 (depends on both Task 1 and Task 2)
        task3_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task 3 - Integration",
                "campaign_id": campaign_id,
                "dependencies": [task1_id, task2_id],
            },
        )
        task3_data = yaml.safe_load(task3_result)
        task3_id = task3_data["data"]["id"]

        # Get all actionable tasks (should be Task 1 and Task 2, not Task 3)
        actionable_result = await service_executor.execute_tool(
            "campaign_get_all_actionable_tasks",
            {"campaign_id": campaign_id},
        )
        actionable_data = yaml.safe_load(actionable_result)
        assert actionable_data["success"] is True
        assert len(actionable_data["data"]["actionable_tasks"]) == 2
        actionable_ids = [t["id"] for t in actionable_data["data"]["actionable_tasks"]]
        assert task1_id in actionable_ids
        assert task2_id in actionable_ids
        assert task3_id not in actionable_ids

        # Complete only Task 1
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task1_id, "status": "done"},
        )

        # Task 3 still should not be actionable
        actionable2_result = await service_executor.execute_tool(
            "campaign_get_all_actionable_tasks",
            {"campaign_id": campaign_id},
        )
        actionable2_data = yaml.safe_load(actionable2_result)
        actionable2_ids = [t["id"] for t in actionable2_data["data"]["actionable_tasks"]]
        assert task3_id not in actionable2_ids

        # Complete Task 2
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task2_id, "status": "done"},
        )

        # Now Task 3 should be actionable
        actionable3_result = await service_executor.execute_tool(
            "campaign_get_all_actionable_tasks",
            {"campaign_id": campaign_id},
        )
        actionable3_data = yaml.safe_load(actionable3_result)
        actionable3_ids = [t["id"] for t in actionable3_data["data"]["actionable_tasks"]]
        assert task3_id in actionable3_ids

    @pytest.mark.asyncio
    async def test_acceptance_criteria_complete_workflow(
        self, service_executor, campaign_with_task
    ):
        """Test complete acceptance criteria workflow."""
        task_id = campaign_with_task["task_id"]

        # Add multiple criteria
        criteria_ids = []
        for i in range(3):
            result = await service_executor.execute_tool(
                "task_acceptance_criteria_add",
                {
                    "task_id": task_id,
                    "content": f"Criterion {i+1}",
                },
            )
            data = yaml.safe_load(result)
            criteria_ids.append(data["data"]["id"])

        # Get task and verify criteria
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert len(show_data["data"]["acceptance_criteria_details"]) == 3

        # Mark some criteria as met
        await service_executor.execute_tool(
            "task_acceptance_criteria_mark_met",
            {"criteria_id": criteria_ids[0]},
        )
        await service_executor.execute_tool(
            "task_acceptance_criteria_mark_met",
            {"criteria_id": criteria_ids[1]},
        )

        # Try to complete task (should fail)
        complete_result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task_id},
        )
        complete_data = yaml.safe_load(complete_result)
        assert complete_data["success"] is False

        # Mark last criterion as met
        await service_executor.execute_tool(
            "task_acceptance_criteria_mark_met",
            {"criteria_id": criteria_ids[2]},
        )

        # Now completion should succeed
        complete2_result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task_id},
        )
        complete2_data = yaml.safe_load(complete2_result)
        assert complete2_data["success"] is True

    @pytest.mark.asyncio
    async def test_task_research_workflow(self, service_executor, campaign_with_task):
        """Test task research item workflow."""
        task_id = campaign_with_task["task_id"]

        # Add different types of research
        research_types = ["findings", "approaches", "docs"]
        for research_type in research_types:
            result = await service_executor.execute_tool(
                "task_research_add",
                {
                    "task_id": task_id,
                    "content": f"Research {research_type} content",
                    "research_type": research_type,
                },
            )
            data = yaml.safe_load(result)
            assert data["success"] is True
            assert data["data"]["type"] == research_type

        # Get task and verify research
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert len(show_data["data"]["research"]) == 3

    @pytest.mark.asyncio
    async def test_task_implementation_notes_workflow(self, service_executor, campaign_with_task):
        """Test implementation notes workflow."""
        task_id = campaign_with_task["task_id"]

        # Add multiple implementation notes
        notes = [
            "Started implementation with data model",
            "Encountered issue with foreign key constraints",
            "Resolved by adjusting migration order",
            "All tests passing now",
        ]

        for note_content in notes:
            result = await service_executor.execute_tool(
                "task_implementation_notes_add",
                {
                    "task_id": task_id,
                    "content": note_content,
                },
            )
            data = yaml.safe_load(result)
            assert data["success"] is True

        # Get task and verify notes
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert len(show_data["data"]["implementation_notes"]) == 4

    @pytest.mark.asyncio
    async def test_task_testing_steps_workflow(self, service_executor, campaign_with_task):
        """Test testing steps workflow."""
        task_id = campaign_with_task["task_id"]

        # Add testing steps in proper order
        steps = [
            ("Create test database", "setup"),
            ("Seed test data", "setup"),
            ("Run authentication test", "trigger"),
            ("Verify token generation", "verify"),
            ("Verify token validation", "verify"),
            ("Clean up test data", "cleanup"),
        ]

        for content, step_type in steps:
            result = await service_executor.execute_tool(
                "task_testing_step_add",
                {
                    "task_id": task_id,
                    "content": content,
                    "step_type": step_type,
                },
            )
            data = yaml.safe_load(result)
            assert data["success"] is True
            assert data["data"]["step_type"] == step_type

        # Get task and verify steps
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert len(show_data["data"]["testing_steps"]) == 6

    @pytest.mark.asyncio
    async def test_task_status_transitions(self, service_executor, campaign_with_task):
        """Test valid task status transitions."""
        task_id = campaign_with_task["task_id"]

        # pending -> in-progress
        result1 = await service_executor.execute_tool(
            "task_update",
            {"task_id": task_id, "status": "in-progress"},
        )
        data1 = yaml.safe_load(result1)
        assert data1["success"] is True
        assert data1["data"]["status"] == "in-progress"

        # in-progress -> blocked
        result2 = await service_executor.execute_tool(
            "task_update",
            {"task_id": task_id, "status": "blocked"},
        )
        data2 = yaml.safe_load(result2)
        assert data2["success"] is True
        assert data2["data"]["status"] == "blocked"

        # blocked -> in-progress
        result3 = await service_executor.execute_tool(
            "task_update",
            {"task_id": task_id, "status": "in-progress"},
        )
        data3 = yaml.safe_load(result3)
        assert data3["success"] is True
        assert data3["data"]["status"] == "in-progress"

        # in-progress -> done (via task_complete, but need criteria)
        # For this test, just update status directly
        result4 = await service_executor.execute_tool(
            "task_update",
            {"task_id": task_id, "status": "done"},
        )
        data4 = yaml.safe_load(result4)
        assert data4["success"] is True
        assert data4["data"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_task_priority_update(self, service_executor, campaign_with_task):
        """Test updating task priority."""
        task_id = campaign_with_task["task_id"]

        # Update priority from medium to critical
        result = await service_executor.execute_tool(
            "task_update",
            {"task_id": task_id, "priority": "critical"},
        )
        data = yaml.safe_load(result)
        assert data["success"] is True
        assert data["data"]["priority"] == "critical"

    @pytest.mark.asyncio
    async def test_task_filtering(self, service_executor):
        """Test task list filtering."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Filter Test Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create tasks with different properties
        await service_executor.execute_tool(
            "task_create",
            {
                "title": "High Priority Pending",
                "campaign_id": campaign_id,
                "priority": "high",
                "status": "pending",
            },
        )
        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Low Priority In Progress",
                "campaign_id": campaign_id,
                "priority": "low",
                "status": "in-progress",
            },
        )
        await service_executor.execute_tool(
            "task_create",
            {
                "title": "High Priority Done",
                "campaign_id": campaign_id,
                "priority": "high",
                "status": "done",
            },
        )

        # Filter by status
        pending_result = await service_executor.execute_tool(
            "task_list",
            {
                "campaign_id": campaign_id,
                "status": "pending",
            },
        )
        pending_data = yaml.safe_load(pending_result)
        assert len(pending_data["data"]) == 1
        assert pending_data["data"][0]["status"] == "pending"

        # Filter by priority
        high_result = await service_executor.execute_tool(
            "task_list",
            {
                "campaign_id": campaign_id,
                "priority": "high",
            },
        )
        high_data = yaml.safe_load(high_result)
        assert len(high_data["data"]) == 2
        for task in high_data["data"]:
            assert task["priority"] == "high"

    @pytest.mark.asyncio
    async def test_task_deletion_cascade(self, service_executor):
        """Test that deleting a task cleans up related data."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Deletion Test"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task to Delete",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Add various related items
        await service_executor.execute_tool(
            "task_acceptance_criteria_add",
            {"task_id": task_id, "content": "Criterion"},
        )
        await service_executor.execute_tool(
            "task_research_add",
            {"task_id": task_id, "content": "Research"},
        )
        await service_executor.execute_tool(
            "task_implementation_notes_add",
            {"task_id": task_id, "content": "Note"},
        )
        await service_executor.execute_tool(
            "task_testing_step_add",
            {"task_id": task_id, "content": "Step"},
        )

        # Delete task
        delete_result = await service_executor.execute_tool(
            "task_delete",
            {"task_id": task_id},
        )
        delete_data = yaml.safe_load(delete_result)
        assert delete_data["success"] is True

        # Verify task is gone
        show_result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        show_data = yaml.safe_load(show_result)
        assert show_data["success"] is False
