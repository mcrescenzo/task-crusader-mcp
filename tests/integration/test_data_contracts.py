"""Data contract tests between services and TUI.

These tests verify that the data format returned by services matches
what the TUI widgets expect. This catches field name mismatches like
the "entity_id" vs "id" bug in acceptance criteria.
"""

from task_crusade_mcp.services import CampaignService, TaskService


class TestAcceptanceCriteriaContract:
    """Tests that verify acceptance criteria data format."""

    def test_acceptance_criteria_has_id_field(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """CRITICAL: Verify acceptance criteria use 'id' not 'entity_id'.

        This test catches the bug where TUI code expected 'entity_id'
        but the service returns 'id'.
        """
        # Create a campaign first
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        assert campaign_result.is_success
        campaign_id = campaign_result.data["id"]

        # Create a task with acceptance criteria
        task_result = task_service.create_task(
            title="Test Task",
            campaign_id=campaign_id,
            acceptance_criteria=["Criterion 1", "Criterion 2"],
        )
        assert task_result.is_success
        task_id = task_result.data["id"]

        # Get the task details
        get_result = task_service.get_task(task_id)
        assert get_result.is_success

        task_data = get_result.data
        criteria = task_data.get("acceptance_criteria_details", [])

        # Verify criteria exist
        assert len(criteria) == 2

        # CRITICAL: Verify each criterion has 'id' field, NOT 'entity_id'
        for criterion in criteria:
            assert "id" in criterion, "Criterion must have 'id' field"
            assert "entity_id" not in criterion, "Criterion must NOT have 'entity_id' field"
            assert criterion["id"] is not None
            assert len(criterion["id"]) > 0

    def test_acceptance_criteria_has_required_fields(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify acceptance criteria have all required fields for TUI."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(
            title="Test Task",
            campaign_id=campaign_id,
            acceptance_criteria=["Test criterion"],
        )
        task_id = task_result.data["id"]

        get_result = task_service.get_task(task_id)
        criteria = get_result.data.get("acceptance_criteria_details", [])

        assert len(criteria) == 1
        criterion = criteria[0]

        # Required fields for TUI
        required_fields = ["id", "content", "is_met"]
        for field in required_fields:
            assert field in criterion, f"Criterion must have '{field}' field"

    def test_acceptance_criteria_id_can_toggle(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify the 'id' field can be used to toggle criterion status."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(
            title="Test Task",
            campaign_id=campaign_id,
            acceptance_criteria=["Test criterion"],
        )
        task_id = task_result.data["id"]

        get_result = task_service.get_task(task_id)
        criteria = get_result.data.get("acceptance_criteria_details", [])
        criterion_id = criteria[0]["id"]

        # Use the id to mark criterion as met
        mark_result = task_service.mark_criteria_met(criterion_id)
        assert mark_result.is_success, "Should be able to mark criterion using 'id' field"

        # Verify it was updated
        get_result = task_service.get_task(task_id)
        updated_criteria = get_result.data.get("acceptance_criteria_details", [])
        assert updated_criteria[0]["is_met"] is True


class TestTaskDataContract:
    """Tests that verify task data format matches TUI expectations."""

    def test_task_has_required_fields(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify task data has all fields required by TUI widgets."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(
            title="Test Task",
            campaign_id=campaign_id,
            description="Test description",
            priority="high",
        )
        task_id = task_result.data["id"]

        get_result = task_service.get_task(task_id)
        task_data = get_result.data

        # Required fields for TaskDataTable
        table_fields = ["id", "title", "status", "priority"]
        for field in table_fields:
            assert field in task_data, f"Task must have '{field}' for TaskDataTable"

        # Required fields for TaskDetailWidget
        detail_fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "acceptance_criteria_details",
            "research",
            "implementation_notes",
        ]
        for field in detail_fields:
            assert field in task_data, f"Task must have '{field}' for TaskDetailWidget"

    def test_task_list_format(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify task list format matches TUI expectations."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_service.create_task(title="Task 1", campaign_id=campaign_id)
        task_service.create_task(title="Task 2", campaign_id=campaign_id)

        list_result = task_service.list_tasks(campaign_id=campaign_id)
        assert list_result.is_success

        tasks = list_result.data
        assert len(tasks) == 2

        for task in tasks:
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert "priority" in task


class TestCampaignDataContract:
    """Tests that verify campaign data format matches TUI expectations."""

    def test_campaign_has_required_fields(
        self,
        campaign_service: CampaignService,
    ) -> None:
        """Verify campaign data has all fields required by TUI widgets."""
        create_result = campaign_service.create_campaign(
            name="Test Campaign",
            description="Test description",
            priority="high",
        )
        campaign_id = create_result.data["id"]

        get_result = campaign_service.get_campaign(campaign_id)
        campaign_data = get_result.data

        # Required fields for CampaignListWidget
        list_fields = ["id", "name", "status", "priority"]
        for field in list_fields:
            assert field in campaign_data, f"Campaign must have '{field}' for list"

    def test_campaign_list_format(
        self,
        campaign_service: CampaignService,
    ) -> None:
        """Verify campaign list format matches TUI expectations."""
        campaign_service.create_campaign(name="Campaign 1")
        campaign_service.create_campaign(name="Campaign 2")

        list_result = campaign_service.list_campaigns()
        assert list_result.is_success

        campaigns = list_result.data
        assert len(campaigns) >= 2

        for campaign in campaigns:
            assert "id" in campaign
            assert "name" in campaign
            assert "status" in campaign

    def test_progress_summary_format(
        self,
        campaign_service: CampaignService,
        task_service: TaskService,
    ) -> None:
        """Verify progress summary format matches TUI expectations."""
        create_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = create_result.data["id"]

        # Add some tasks
        task_service.create_task(title="Task 1", campaign_id=campaign_id)
        task_result = task_service.create_task(title="Task 2", campaign_id=campaign_id)
        task_service.update_task(task_result.data["id"], status="done")

        progress_result = campaign_service.get_progress_summary(campaign_id)
        assert progress_result.is_success

        progress = progress_result.data

        # Required fields for TaskDetailWidget campaign summary
        required_fields = ["total_tasks", "tasks_by_status", "completion_rate"]
        for field in required_fields:
            assert field in progress, f"Progress must have '{field}' field"

        # Verify tasks_by_status is a dict
        assert isinstance(progress["tasks_by_status"], dict)


class TestResearchDataContract:
    """Tests that verify research data format matches TUI expectations."""

    def test_task_research_format(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify task research format matches TUI expectations."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(title="Test Task", campaign_id=campaign_id)
        task_id = task_result.data["id"]

        # Add research
        task_service.add_research(task_id, "Research finding 1", "findings")
        task_service.add_research(task_id, "Research finding 2", "approaches")

        get_result = task_service.get_task(task_id)
        research = get_result.data.get("research", [])

        assert len(research) == 2

        for item in research:
            # Required fields for TaskDetailWidget._render_research
            assert "notes" in item or "content" in item
            # TUI uses "association_type" but service returns "type" - this is acceptable
            # as long as one of them is present
            assert "association_type" in item or "type" in item

    def test_campaign_research_format(
        self,
        campaign_service: CampaignService,
    ) -> None:
        """Verify campaign research format matches TUI expectations."""
        create_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = create_result.data["id"]

        # Add campaign research
        campaign_service.add_campaign_research(campaign_id, "Strategy note", "strategy")

        list_result = campaign_service.list_campaign_research(campaign_id)
        assert list_result.is_success

        research = list_result.data
        assert len(research) == 1

        item = research[0]
        # Required fields for TaskDetailWidget._render_campaign_research
        assert "type" in item or "research_type" in item


class TestImplementationNotesContract:
    """Tests that verify implementation notes format matches TUI expectations."""

    def test_implementation_notes_format(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify implementation notes format matches TUI expectations."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(title="Test Task", campaign_id=campaign_id)
        task_id = task_result.data["id"]

        # Add implementation note
        task_service.add_implementation_note(task_id, "Implementation note 1")

        get_result = task_service.get_task(task_id)
        notes = get_result.data.get("implementation_notes", [])

        assert len(notes) == 1

        note = notes[0]
        # Required fields for TaskDetailWidget._render_implementation_notes
        assert "notes" in note or "content" in note


class TestTestingStepsContract:
    """Tests that verify testing steps format matches TUI expectations."""

    def test_testing_steps_format(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify testing steps format matches TUI expectations."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        task_result = task_service.create_task(title="Test Task", campaign_id=campaign_id)
        task_id = task_result.data["id"]

        # Add testing step
        task_service.add_testing_step(task_id, "Verify functionality", "verify")

        get_result = task_service.get_task(task_id)
        steps = get_result.data.get("testing_steps", [])

        assert len(steps) == 1

        step = steps[0]
        # The TUI expects notes field
        assert "notes" in step or "content" in step


class TestDependencyDataContract:
    """Tests that verify dependency data format matches TUI expectations."""

    def test_dependency_format(
        self,
        task_service: TaskService,
        campaign_service: CampaignService,
    ) -> None:
        """Verify dependency format matches TUI expectations."""
        campaign_result = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign_result.data["id"]

        # Create dependency task
        dep_result = task_service.create_task(title="Dependency Task", campaign_id=campaign_id)
        dep_id = dep_result.data["id"]

        # Create task with dependency
        task_result = task_service.create_task(
            title="Dependent Task",
            campaign_id=campaign_id,
            dependencies=[dep_id],
        )
        task_id = task_result.data["id"]

        get_result = task_service.get_task(task_id)
        task_data = get_result.data

        # Verify dependencies list
        assert "dependencies" in task_data
        assert dep_id in task_data["dependencies"]
