"""Integration tests for campaign workflows."""

import pytest
import yaml

from task_crusade_mcp.server.service_executor import ServiceExecutor


@pytest.fixture
def service_executor():
    """Create a service executor with test database."""
    executor = ServiceExecutor()
    yield executor
    executor.close()


class TestCampaignWorkflows:
    """Test end-to-end campaign workflows."""

    @pytest.mark.asyncio
    async def test_complete_campaign_workflow(self, service_executor):
        """Test a complete campaign workflow from creation to completion."""
        # Step 1: Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {
                "name": "Website Redesign",
                "description": "Complete redesign of company website",
                "priority": "high",
                "status": "planning",
            },
        )
        campaign_data = yaml.safe_load(campaign_result)
        assert campaign_data["success"] is True
        campaign_id = campaign_data["data"]["id"]

        # Step 2: Add campaign research
        research1_result = await service_executor.execute_tool(
            "campaign_research_add",
            {
                "campaign_id": campaign_id,
                "content": "User research indicates need for mobile-first design",
                "research_type": "strategy",
            },
        )
        research1_data = yaml.safe_load(research1_result)
        assert research1_data["success"] is True

        research2_result = await service_executor.execute_tool(
            "campaign_research_add",
            {
                "campaign_id": campaign_id,
                "content": "Current site has 60% mobile traffic",
                "research_type": "analysis",
            },
        )
        research2_data = yaml.safe_load(research2_result)
        assert research2_data["success"] is True

        # Step 3: Create tasks with dependencies
        # Task 1: Design mockups (no dependencies)
        task1_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Create design mockups",
                "campaign_id": campaign_id,
                "description": "Design mobile-first mockups",
                "priority": "critical",
                "type": "code",
                "acceptance_criteria": [
                    "Mockups approved by stakeholders",
                    "Mobile and desktop versions created",
                ],
            },
        )
        task1_data = yaml.safe_load(task1_result)
        assert task1_data["success"] is True
        task1_id = task1_data["data"]["id"]

        # Task 2: Implement frontend (depends on Task 1)
        task2_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Implement frontend",
                "campaign_id": campaign_id,
                "description": "Build responsive frontend",
                "priority": "high",
                "type": "code",
                "dependencies": [task1_id],
                "acceptance_criteria": [
                    "All pages are responsive",
                    "Pass accessibility tests",
                ],
            },
        )
        task2_data = yaml.safe_load(task2_result)
        assert task2_data["success"] is True
        task2_id = task2_data["data"]["id"]

        # Task 3: Deploy (depends on Task 2)
        task3_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Deploy to production",
                "campaign_id": campaign_id,
                "description": "Deploy new website",
                "priority": "critical",
                "type": "deployment",
                "dependencies": [task2_id],
                "acceptance_criteria": [
                    "Deployed successfully",
                    "No errors in production logs",
                ],
            },
        )
        task3_data = yaml.safe_load(task3_result)
        assert task3_data["success"] is True
        task3_id = task3_data["data"]["id"]

        # Step 4: Check initial progress
        progress_result = await service_executor.execute_tool(
            "campaign_get_progress_summary",
            {"campaign_id": campaign_id},
        )
        progress_data = yaml.safe_load(progress_result)
        assert progress_data["success"] is True
        assert progress_data["data"]["total_tasks"] == 3
        assert progress_data["data"]["tasks_by_status"]["pending"] == 3
        assert progress_data["data"]["completion_rate"] == 0.0

        # Step 5: Get next actionable task (should be Task 1, no dependencies)
        next_task_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next_task_data = yaml.safe_load(next_task_result)
        assert next_task_data["success"] is True
        assert next_task_data["data"]["task"]["id"] == task1_id

        # Step 6: Work on Task 1
        # Update status to in-progress
        update_result = await service_executor.execute_tool(
            "task_update",
            {
                "task_id": task1_id,
                "status": "in-progress",
            },
        )
        update_data = yaml.safe_load(update_result)
        assert update_data["success"] is True

        # Add implementation notes
        note_result = await service_executor.execute_tool(
            "task_implementation_notes_add",
            {
                "task_id": task1_id,
                "content": "Using Figma for mockup creation",
            },
        )
        note_data = yaml.safe_load(note_result)
        assert note_data["success"] is True

        # Mark acceptance criteria as met
        for criterion in task1_data["data"]["acceptance_criteria_details"]:
            criteria_result = await service_executor.execute_tool(
                "task_acceptance_criteria_mark_met",
                {"criteria_id": criterion["id"]},
            )
            criteria_data = yaml.safe_load(criteria_result)
            assert criteria_data["success"] is True

        # Complete Task 1
        complete1_result = await service_executor.execute_tool(
            "task_complete",
            {"task_id": task1_id},
        )
        complete1_data = yaml.safe_load(complete1_result)
        assert complete1_data["success"] is True

        # Step 7: Check progress after completing Task 1
        progress2_result = await service_executor.execute_tool(
            "campaign_get_progress_summary",
            {"campaign_id": campaign_id},
        )
        progress2_data = yaml.safe_load(progress2_result)
        assert progress2_data["success"] is True
        assert progress2_data["data"]["tasks_by_status"]["done"] == 1
        assert progress2_data["data"]["completion_rate"] == pytest.approx(33.33, 0.1)

        # Step 8: Get next actionable task (should be Task 2 now)
        next_task2_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next_task2_data = yaml.safe_load(next_task2_result)
        assert next_task2_data["success"] is True
        assert next_task2_data["data"]["task"]["id"] == task2_id

        # Step 9: Complete Task 2
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task2_id, "status": "in-progress"},
        )
        for criterion in task2_data["data"]["acceptance_criteria_details"]:
            await service_executor.execute_tool(
                "task_acceptance_criteria_mark_met",
                {"criteria_id": criterion["id"]},
            )
        await service_executor.execute_tool(
            "task_complete",
            {"task_id": task2_id},
        )

        # Step 10: Complete Task 3
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task3_id, "status": "in-progress"},
        )
        for criterion in task3_data["data"]["acceptance_criteria_details"]:
            await service_executor.execute_tool(
                "task_acceptance_criteria_mark_met",
                {"criteria_id": criterion["id"]},
            )
        await service_executor.execute_tool(
            "task_complete",
            {"task_id": task3_id},
        )

        # Step 11: Check final progress
        final_progress_result = await service_executor.execute_tool(
            "campaign_get_progress_summary",
            {"campaign_id": campaign_id},
        )
        final_progress_data = yaml.safe_load(final_progress_result)
        assert final_progress_data["success"] is True
        assert final_progress_data["data"]["tasks_by_status"]["done"] == 3
        assert final_progress_data["data"]["completion_rate"] == 100.0

        # Step 12: Update campaign to completed
        campaign_update_result = await service_executor.execute_tool(
            "campaign_update",
            {
                "campaign_id": campaign_id,
                "status": "completed",
            },
        )
        campaign_update_data = yaml.safe_load(campaign_update_result)
        assert campaign_update_data["success"] is True

    @pytest.mark.asyncio
    async def test_parallel_actionable_tasks(self, service_executor):
        """Test getting multiple actionable tasks for parallel execution."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Parallel Project"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create multiple tasks with no dependencies
        task_ids = []
        for i in range(5):
            task_result = await service_executor.execute_tool(
                "task_create",
                {
                    "title": f"Independent Task {i+1}",
                    "campaign_id": campaign_id,
                    "priority": "medium",
                },
            )
            task_data = yaml.safe_load(task_result)
            task_ids.append(task_data["data"]["id"])

        # Get all actionable tasks
        actionable_result = await service_executor.execute_tool(
            "campaign_get_all_actionable_tasks",
            {
                "campaign_id": campaign_id,
                "max_results": 10,
            },
        )
        actionable_data = yaml.safe_load(actionable_result)

        assert actionable_data["success"] is True
        assert len(actionable_data["data"]["actionable_tasks"]) == 5
        # All should be actionable since no dependencies
        for task_id in task_ids:
            assert any(
                t["id"] == task_id for t in actionable_data["data"]["actionable_tasks"]
            ), f"Task {task_id} should be actionable"

    @pytest.mark.asyncio
    async def test_campaign_with_blocked_tasks(self, service_executor):
        """Test campaign workflow with blocked tasks."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Blocked Tasks Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create Task 1
        task1_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Foundation Task",
                "campaign_id": campaign_id,
            },
        )
        task1_data = yaml.safe_load(task1_result)
        task1_id = task1_data["data"]["id"]

        # Create Task 2 (depends on Task 1)
        task2_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Dependent Task",
                "campaign_id": campaign_id,
                "dependencies": [task1_id],
            },
        )
        task2_data = yaml.safe_load(task2_result)
        task2_id = task2_data["data"]["id"]

        # Get next actionable task (should only be Task 1)
        next_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next_data = yaml.safe_load(next_result)
        assert next_data["success"] is True
        assert next_data["data"]["task"]["id"] == task1_id

        # Block Task 1
        block_result = await service_executor.execute_tool(
            "task_update",
            {"task_id": task1_id, "status": "blocked"},
        )
        block_data = yaml.safe_load(block_result)
        assert block_data["success"] is True

        # Get next actionable task (should be None now)
        next2_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next2_data = yaml.safe_load(next2_result)
        # Should succeed but return None or appropriate message
        assert next2_data["success"] is True

        # Unblock and complete Task 1
        await service_executor.execute_tool(
            "task_update",
            {"task_id": task1_id, "status": "done"},
        )

        # Now Task 2 should be actionable
        next3_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next3_data = yaml.safe_load(next3_result)
        assert next3_data["success"] is True
        assert next3_data["data"]["task"]["id"] == task2_id

    @pytest.mark.asyncio
    async def test_campaign_priority_ordering(self, service_executor):
        """Test that tasks are returned in priority order."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Priority Test Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Create tasks with different priorities
        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Low Priority Task",
                "campaign_id": campaign_id,
                "priority": "low",
            },
        )
        critical_result = await service_executor.execute_tool(
            "task_create",
            {
                "title": "Critical Priority Task",
                "campaign_id": campaign_id,
                "priority": "critical",
            },
        )
        critical_data = yaml.safe_load(critical_result)
        critical_id = critical_data["data"]["id"]

        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Medium Priority Task",
                "campaign_id": campaign_id,
                "priority": "medium",
            },
        )

        # Get next actionable task (should be critical priority)
        next_result = await service_executor.execute_tool(
            "campaign_get_next_actionable_task",
            {"campaign_id": campaign_id},
        )
        next_data = yaml.safe_load(next_result)
        assert next_data["success"] is True
        assert next_data["data"]["task"]["id"] == critical_id
        assert next_data["data"]["task"]["priority"] == "critical"

    @pytest.mark.asyncio
    async def test_campaign_research_workflow(self, service_executor):
        """Test adding and listing campaign research items."""
        # Create campaign
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Research Campaign"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        # Add different types of research
        research_items = [
            {"type": "strategy", "content": "Strategic analysis of market"},
            {"type": "analysis", "content": "Technical feasibility analysis"},
            {"type": "requirements", "content": "User requirements gathered"},
        ]

        for item in research_items:
            result = await service_executor.execute_tool(
                "campaign_research_add",
                {
                    "campaign_id": campaign_id,
                    "content": item["content"],
                    "research_type": item["type"],
                },
            )
            data = yaml.safe_load(result)
            assert data["success"] is True

        # List all research
        list_result = await service_executor.execute_tool(
            "campaign_research_list",
            {"campaign_id": campaign_id},
        )
        list_data = yaml.safe_load(list_result)
        assert list_data["success"] is True
        assert len(list_data["data"]) == 3

        # List filtered research
        strategy_result = await service_executor.execute_tool(
            "campaign_research_list",
            {
                "campaign_id": campaign_id,
                "research_type": "strategy",
            },
        )
        strategy_data = yaml.safe_load(strategy_result)
        assert strategy_data["success"] is True
        assert len(strategy_data["data"]) == 1
        assert strategy_data["data"][0]["research_type"] == "strategy"

    @pytest.mark.asyncio
    async def test_campaign_details_vs_show(self, service_executor):
        """Test campaign_details vs campaign_show."""
        # Create campaign with tasks
        campaign_result = await service_executor.execute_tool(
            "campaign_create",
            {"name": "Details Test"},
        )
        campaign_data = yaml.safe_load(campaign_result)
        campaign_id = campaign_data["data"]["id"]

        await service_executor.execute_tool(
            "task_create",
            {
                "title": "Test Task",
                "campaign_id": campaign_id,
            },
        )

        # Get campaign details (metadata only)
        details_result = await service_executor.execute_tool(
            "campaign_details",
            {"campaign_id": campaign_id},
        )
        details_data = yaml.safe_load(details_result)
        assert details_data["success"] is True
        assert "name" in details_data["data"]
        assert "id" in details_data["data"]

        # Get campaign show (includes tasks)
        show_result = await service_executor.execute_tool(
            "campaign_show",
            {"campaign_id": campaign_id},
        )
        show_data = yaml.safe_load(show_result)
        assert show_data["success"] is True
        assert "name" in show_data["data"]
        assert "tasks" in show_data["data"]
        assert len(show_data["data"]["tasks"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_campaigns(self, service_executor):
        """Test managing multiple campaigns simultaneously."""
        # Create multiple campaigns
        campaign_ids = []
        for i in range(3):
            result = await service_executor.execute_tool(
                "campaign_create",
                {
                    "name": f"Campaign {i+1}",
                    "priority": ["low", "medium", "high"][i],
                    "status": ["planning", "active", "active"][i],
                },
            )
            data = yaml.safe_load(result)
            campaign_ids.append(data["data"]["id"])

        # List all campaigns
        list_result = await service_executor.execute_tool("campaign_list", {})
        list_data = yaml.safe_load(list_result)
        assert list_data["success"] is True
        assert len(list_data["data"]) == 3

        # List filtered by status
        active_result = await service_executor.execute_tool(
            "campaign_list",
            {"status": "active"},
        )
        active_data = yaml.safe_load(active_result)
        assert active_data["success"] is True
        assert len(active_data["data"]) == 2

        # List filtered by priority
        high_result = await service_executor.execute_tool(
            "campaign_list",
            {"priority": "high"},
        )
        high_data = yaml.safe_load(high_result)
        assert high_data["success"] is True
        assert len(high_data["data"]) == 1
        assert high_data["data"][0]["priority"] == "high"
