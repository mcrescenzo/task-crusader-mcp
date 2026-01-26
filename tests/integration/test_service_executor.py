"""Integration tests for ServiceExecutor."""

import pytest
import yaml

from task_crusade_mcp.server.service_executor import ServiceExecutor


@pytest.fixture
def service_executor():
    """Create a service executor with test database."""
    executor = ServiceExecutor()
    yield executor
    executor.close()


class TestCampaignTools:
    """Test campaign tool execution via ServiceExecutor."""

    @pytest.mark.asyncio
    async def test_campaign_create(self, service_executor):
        """Test creating a campaign via executor."""
        result = await service_executor.execute_tool(
            "campaign_create",
            {
                "name": "Test Campaign",
                "description": "Integration test campaign",
                "priority": "high",
            },
        )

        # Parse YAML result
        data = yaml.safe_load(result)
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["name"] == "Test Campaign"
        assert data["data"]["priority"] == "high"
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_campaign_list(self, service_executor):
        """Test listing campaigns."""
        # Create a campaign first
        await service_executor.execute_tool(
            "campaign_create",
            {"name": "Campaign 1", "priority": "medium"},
        )

        # List campaigns
        result = await service_executor.execute_tool("campaign_list", {})
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["data"][0]["name"] == "Campaign 1"

    @pytest.mark.asyncio
    async def test_campaign_list_with_filter(self, service_executor):
        """Test listing campaigns with status filter."""
        # Create campaigns with different statuses
        await service_executor.execute_tool(
            "campaign_create",
            {"name": "Active Campaign", "status": "active"},
        )
        await service_executor.execute_tool(
            "campaign_create",
            {"name": "Planning Campaign", "status": "planning"},
        )

        # List only active campaigns
        result = await service_executor.execute_tool(
            "campaign_list",
            {"status": "active"},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_campaign_show(self, service_executor):
        """Test showing campaign details."""
        # Create campaign
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Detail Test"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Show campaign
        result = await service_executor.execute_tool(
            "campaign_show",
            {"campaign_id": campaign_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["name"] == "Detail Test"
        assert "tasks" in data["data"]

    @pytest.mark.asyncio
    async def test_campaign_update(self, service_executor):
        """Test updating a campaign."""
        # Create campaign
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Update Test", "priority": "low"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Update campaign
        result = await service_executor.execute_tool(
            "campaign_update",
            {
                "campaign_id": campaign_id,
                "priority": "critical",
                "status": "active",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["priority"] == "critical"
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_campaign_delete(self, service_executor):
        """Test deleting a campaign."""
        # Create campaign
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Delete Test"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Delete campaign
        result = await service_executor.execute_tool(
            "campaign_delete",
            {"campaign_id": campaign_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert "deleted" in data["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_campaign_progress_summary(self, service_executor):
        """Test getting campaign progress summary."""
        # Create campaign with tasks
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Progress Test"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Create task
        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Test Task",
                "campaign_id": campaign_id,
            },
        )

        # Get progress
        result = await service_executor.execute_tool(
            "campaign_get_progress_summary",
            {"campaign_id": campaign_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert "total_tasks" in data["data"]
        assert data["data"]["total_tasks"] == 1

    @pytest.mark.asyncio
    async def test_campaign_research_add(self, service_executor):
        """Test adding research to campaign."""
        # Create campaign
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Research Test"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Add research
        result = await service_executor.execute_tool(
            "campaign_research_add",
            {
                "campaign_id": campaign_id,
                "content": "This is research content",
                "research_type": "strategy",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["content"] == "This is research content"
        assert data["data"]["research_type"] == "strategy"

    @pytest.mark.asyncio
    async def test_campaign_research_list(self, service_executor):
        """Test listing campaign research."""
        # Create campaign
        create_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Research List Test"},
        )
        create_data = yaml.safe_load(create_result)
        campaign_id = create_data["data"]["id"]

        # Add research items
        await service_executor.execute_tool(
            "campaign_research_add",
            {
                "campaign_id": campaign_id,
                "content": "Strategy research",
                "research_type": "strategy",
            },
        )
        await service_executor.execute_tool(
            "campaign_research_add",
            {
                "campaign_id": campaign_id,
                "content": "Analysis research",
                "research_type": "analysis",
            },
        )

        # List all research
        result = await service_executor.execute_tool(
            "campaign_research_list",
            {"campaign_id": campaign_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_campaign_workflow_guide(self, service_executor):
        """Test getting workflow guide."""
        result = await service_executor.execute_tool("campaign_workflow_guide", {})
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert "title" in data["data"]
        assert "phases" in data["data"]
        assert len(data["data"]["phases"]) == 3

    @pytest.mark.asyncio
    async def test_unknown_tool(self, service_executor):
        """Test handling of unknown tool."""
        result = await service_executor.execute_tool("unknown_tool", {})
        data = yaml.safe_load(result)

        assert data["success"] is False
        assert "Unknown tool" in data["error"]


class TestTaskTools:
    """Test task tool execution via ServiceExecutor."""

    @pytest.mark.asyncio
    async def test_task_create(self, service_executor):
        """Test creating a task via executor."""
        # Create campaign first
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Task Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create task
        result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Test Task",
                "campaign_id": campaign_id,
                "description": "Task description",
                "priority": "high",
                "type": "code",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["title"] == "Test Task"
        assert data["data"]["priority"] == "high"
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_task_create_with_criteria(self, service_executor):
        """Test creating task with acceptance criteria."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Criteria Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create task with criteria
        result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task with Criteria",
                "campaign_id": campaign_id,
                "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert len(data["data"]["acceptance_criteria_details"]) == 2

    @pytest.mark.asyncio
    async def test_task_list(self, service_executor):
        """Test listing tasks."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "List Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Task 1",
                "campaign_id": campaign_id,
            },
        )

        # List tasks
        result = await service_executor.execute_tool(
            "task_list",
            {"campaign_id": campaign_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Task 1"

    @pytest.mark.asyncio
    async def test_task_show(self, service_executor):
        """Test showing task details."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Show Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Show Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Show task
        result = await service_executor.execute_tool(
            "task_show",
            {"task_id": task_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["title"] == "Show Task"

    @pytest.mark.asyncio
    async def test_task_update(self, service_executor):
        """Test updating a task."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Update Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Update Task",
                "campaign_id": campaign_id,
                "priority": "low",
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Update task
        result = await service_executor.execute_tool(
            "task_update",
            {
                "task_id": task_id,
                "priority": "critical",
                "status": "in-progress",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["priority"] == "critical"
        assert data["data"]["status"] == "in-progress"

    @pytest.mark.asyncio
    async def test_task_delete(self, service_executor):
        """Test deleting a task."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Delete Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Delete Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Delete task
        result = await service_executor.execute_tool(
            "task_delete",
            {"task_id": task_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_acceptance_criteria_workflow(self, service_executor):
        """Test full acceptance criteria workflow."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Criteria Workflow"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Criteria Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Add criteria
        add_result = await service_executor.execute_tool(
            "task_acceptance_criteria_add",
            {
                "task_id": task_id,
                "content": "Feature works correctly",
            },
        )
        add_data = yaml.safe_load(add_result)
        criteria_id = add_data["data"]["id"]

        assert add_data["success"] is True
        assert add_data["data"]["is_met"] is False

        # Mark as met
        met_result = await service_executor.execute_tool(
            "task_acceptance_criteria_mark_met",
            {"criteria_id": criteria_id},
        )
        met_data = yaml.safe_load(met_result)

        assert met_data["success"] is True
        assert met_data["data"]["is_met"] is True

        # Mark as unmet
        unmet_result = await service_executor.execute_tool(
            "task_acceptance_criteria_mark_unmet",
            {"criteria_id": criteria_id},
        )
        unmet_data = yaml.safe_load(unmet_result)

        assert unmet_data["success"] is True
        assert unmet_data["data"]["is_met"] is False

    @pytest.mark.asyncio
    async def test_task_research_add(self, service_executor):
        """Test adding research to task."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Research Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Research Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Add research
        result = await service_executor.execute_tool(
            "task_research_add",
            {
                "task_id": task_id,
                "content": "Research findings",
                "research_type": "findings",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["content"] == "Research findings"

    @pytest.mark.asyncio
    async def test_task_implementation_notes_add(self, service_executor):
        """Test adding implementation notes."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Notes Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Notes Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Add note
        result = await service_executor.execute_tool(
            "task_implementation_notes_add",
            {
                "task_id": task_id,
                "content": "Implementation note",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["content"] == "Implementation note"

    @pytest.mark.asyncio
    async def test_task_testing_step_add(self, service_executor):
        """Test adding testing steps."""
        # Create campaign and task
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Testing Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Testing Task",
                "campaign_id": campaign_id,
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Add testing step
        result = await service_executor.execute_tool(
            "task_testing_step_add",
            {
                "task_id": task_id,
                "content": "Run unit tests",
                "step_type": "verify",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["content"] == "Run unit tests"
        assert data["data"]["step_type"] == "verify"

    @pytest.mark.asyncio
    async def test_task_complete_workflow(self, service_executor):
        """Test completing a task with all criteria met."""
        # Create campaign and task with criteria
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Complete Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Complete Task",
                "campaign_id": campaign_id,
                "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Mark criteria as met
        for criterion in task_data["data"]["acceptance_criteria_details"]:
            await service_executor.execute_tool(
                "task_acceptance_criteria_mark_met",
                {"criteria_id": criterion["id"]},
            )

        # Complete task
        result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is True
        assert data["data"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_task_complete_fails_without_criteria(self, service_executor):
        """Test that completing a task fails when criteria not met."""
        # Create campaign and task with criteria
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Fail Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        task_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Fail Task",
                "campaign_id": campaign_id,
                "acceptance_criteria": ["Unmet criterion"],
            },
        )
        task_data = yaml.safe_load(task_result)
        task_id = task_data["data"]["id"]

        # Try to complete without meeting criteria
        result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task_id},
        )
        data = yaml.safe_load(result)

        assert data["success"] is False
        assert "acceptance criteria" in data["error"].lower()


class TestErrorHandling:
    """Test error handling in ServiceExecutor."""

    @pytest.mark.asyncio
    async def test_campaign_not_found(self, service_executor):
        """Test error when campaign doesn't exist."""
        result = await service_executor.execute_tool(
            "campaign_show",
            {"campaign_id": "nonexistent"},
        )
        data = yaml.safe_load(result)

        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_task_not_found(self, service_executor):
        """Test error when task doesn't exist."""
        result = await service_executor.execute_tool(
            "task_show",
            {"task_id": "nonexistent"},
        )
        data = yaml.safe_load(result)

        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_campaign_name(self, service_executor):
        """Test error with invalid campaign name."""
        result = await service_executor.execute_tool(
            "campaign_create",
            {"name": ""},  # Empty name
        )
        data = yaml.safe_load(result)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_invalid_priority(self, service_executor):
        """Test error with invalid priority value."""
        result = await service_executor.execute_tool(
            "campaign_create",
            {
                "name": "Test",
                "priority": "invalid_priority",
            },
        )
        data = yaml.safe_load(result)

        assert data["success"] is False
