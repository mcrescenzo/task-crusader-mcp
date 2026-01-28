"""Tests for task service."""


class TestTaskService:
    """Tests for TaskService."""

    def test_create_task(self, task_service, campaign_service):
        """Test creating a task."""
        # Create campaign first
        campaign = campaign_service.create_campaign(name="Test Campaign")
        campaign_id = campaign.data["id"]

        result = task_service.create_task(
            title="Test Task",
            campaign_id=campaign_id,
            description="A test task",
            priority="high",
        )

        assert result.is_success
        assert result.data["title"] == "Test Task"
        assert result.data["description"] == "A test task"
        assert result.data["priority"] == "high"
        assert result.data["status"] == "pending"

    def test_create_task_nonexistent_campaign(self, task_service):
        """Test creating a task for nonexistent campaign fails."""
        result = task_service.create_task(
            title="Test",
            campaign_id="nonexistent",
        )

        assert result.is_failure

    def test_create_task_with_acceptance_criteria(self, task_service, campaign_service):
        """Test creating a task with acceptance criteria."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        result = task_service.create_task(
            title="Task with Criteria",
            campaign_id=campaign_id,
            acceptance_criteria=["Criterion 1", "Criterion 2"],
        )

        assert result.is_success
        assert len(result.data.get("acceptance_criteria_details", [])) == 2

    def test_get_task(self, task_service, campaign_service):
        """Test getting a task."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        result = task_service.get_task(task_id)

        assert result.is_success
        assert result.data["id"] == task_id
        assert "acceptance_criteria_details" in result.data

    def test_update_task(self, task_service, campaign_service):
        """Test updating a task."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Original", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        result = task_service.update_task(task_id, title="Updated", status="in-progress")

        assert result.is_success
        assert result.data["title"] == "Updated"
        assert result.data["status"] == "in-progress"

    def test_add_acceptance_criteria(self, task_service, campaign_service):
        """Test adding acceptance criteria."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        result = task_service.add_acceptance_criteria(task_id, "Must pass tests")

        assert result.is_success
        assert result.data["content"] == "Must pass tests"
        assert result.data["is_met"] is False

    def test_mark_criteria_met(self, task_service, campaign_service):
        """Test marking acceptance criteria as met."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        criteria = task_service.add_acceptance_criteria(task_id, "Test criterion")
        criteria_id = criteria.data["id"]

        result = task_service.mark_criteria_met(criteria_id)

        assert result.is_success
        assert result.data["is_met"] is True

    def test_complete_task_without_criteria(self, task_service, campaign_service):
        """Test completing a task without criteria succeeds."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        result = task_service.complete_task(task_id)

        assert result.is_success
        assert result.data["status"] == "done"

    def test_complete_task_with_unmet_criteria(self, task_service, campaign_service):
        """Test completing a task with unmet criteria fails."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        task_service.add_acceptance_criteria(task_id, "Unmet criterion")

        result = task_service.complete_task(task_id)

        assert result.is_failure
        assert "criteria" in result.error_message.lower()

    def test_complete_task_with_met_criteria(self, task_service, campaign_service):
        """Test completing a task with all criteria met succeeds."""
        campaign = campaign_service.create_campaign(name="Test")
        task = task_service.create_task(title="Test", campaign_id=campaign.data["id"])
        task_id = task.data["id"]

        criteria = task_service.add_acceptance_criteria(task_id, "Must pass")
        task_service.mark_criteria_met(criteria.data["id"])

        result = task_service.complete_task(task_id)

        assert result.is_success
        assert result.data["status"] == "done"

    # --- Dependency Management Tests ---

    def test_update_task_add_dependencies(self, task_service, campaign_service):
        """Test adding dependencies to a task using add_dependencies."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        # Create dependency tasks
        dep1 = task_service.create_task(title="Dep 1", campaign_id=campaign_id)
        dep2 = task_service.create_task(title="Dep 2", campaign_id=campaign_id)
        dep3 = task_service.create_task(title="Dep 3", campaign_id=campaign_id)

        # Create main task with one dependency
        main_task = task_service.create_task(
            title="Main Task",
            campaign_id=campaign_id,
            dependencies=[dep1.data["id"]],
        )
        main_task_id = main_task.data["id"]

        # Add more dependencies
        result = task_service.update_task(
            main_task_id,
            add_dependencies=[dep2.data["id"], dep3.data["id"]],
        )

        assert result.is_success
        assert len(result.data["dependencies"]) == 3
        assert dep1.data["id"] in result.data["dependencies"]
        assert dep2.data["id"] in result.data["dependencies"]
        assert dep3.data["id"] in result.data["dependencies"]

    def test_update_task_add_dependencies_no_duplicates(self, task_service, campaign_service):
        """Test that add_dependencies doesn't create duplicates."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        dep = task_service.create_task(title="Dep", campaign_id=campaign_id)
        main_task = task_service.create_task(
            title="Main",
            campaign_id=campaign_id,
            dependencies=[dep.data["id"]],
        )

        # Try to add the same dependency again
        result = task_service.update_task(
            main_task.data["id"],
            add_dependencies=[dep.data["id"]],
        )

        assert result.is_success
        # Should still only have one dependency (no duplicate)
        assert len(result.data["dependencies"]) == 1

    def test_update_task_remove_dependencies(self, task_service, campaign_service):
        """Test removing dependencies from a task using remove_dependencies."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        # Create dependency tasks
        dep1 = task_service.create_task(title="Dep 1", campaign_id=campaign_id)
        dep2 = task_service.create_task(title="Dep 2", campaign_id=campaign_id)

        # Create main task with both dependencies
        main_task = task_service.create_task(
            title="Main Task",
            campaign_id=campaign_id,
            dependencies=[dep1.data["id"], dep2.data["id"]],
        )
        main_task_id = main_task.data["id"]

        # Remove one dependency
        result = task_service.update_task(
            main_task_id,
            remove_dependencies=[dep1.data["id"]],
        )

        assert result.is_success
        assert len(result.data["dependencies"]) == 1
        assert dep2.data["id"] in result.data["dependencies"]
        assert dep1.data["id"] not in result.data["dependencies"]

    def test_update_task_remove_all_dependencies(self, task_service, campaign_service):
        """Test removing all dependencies from a task."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        dep = task_service.create_task(title="Dep", campaign_id=campaign_id)
        main_task = task_service.create_task(
            title="Main",
            campaign_id=campaign_id,
            dependencies=[dep.data["id"]],
        )

        # Remove the only dependency
        result = task_service.update_task(
            main_task.data["id"],
            remove_dependencies=[dep.data["id"]],
        )

        assert result.is_success
        assert len(result.data["dependencies"]) == 0

    def test_update_task_multiple_dependency_ops_rejected(self, task_service, campaign_service):
        """Test that providing multiple dependency operations fails."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        dep = task_service.create_task(title="Dep", campaign_id=campaign_id)
        main_task = task_service.create_task(title="Main", campaign_id=campaign_id)

        # Try to use both dependencies and add_dependencies
        result = task_service.update_task(
            main_task.data["id"],
            dependencies=[dep.data["id"]],
            add_dependencies=[dep.data["id"]],
        )

        assert result.is_failure
        assert "only one" in result.error_message.lower()

    def test_update_task_add_and_remove_rejected(self, task_service, campaign_service):
        """Test that providing both add and remove operations fails."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        dep = task_service.create_task(title="Dep", campaign_id=campaign_id)
        main_task = task_service.create_task(
            title="Main",
            campaign_id=campaign_id,
            dependencies=[dep.data["id"]],
        )

        # Try to use both add_dependencies and remove_dependencies
        result = task_service.update_task(
            main_task.data["id"],
            add_dependencies=[dep.data["id"]],
            remove_dependencies=[dep.data["id"]],
        )

        assert result.is_failure
        assert "only one" in result.error_message.lower()

    def test_update_task_add_dependencies_validates_existence(self, task_service, campaign_service):
        """Test that add_dependencies validates task IDs exist."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        main_task = task_service.create_task(title="Main", campaign_id=campaign_id)

        # Try to add a non-existent dependency
        result = task_service.update_task(
            main_task.data["id"],
            add_dependencies=["nonexistent-task-id"],
        )

        assert result.is_failure
        assert "invalid" in result.error_message.lower()

    def test_update_task_add_dependencies_rejects_self_dependency(
        self, task_service, campaign_service
    ):
        """Test that a task cannot depend on itself via add_dependencies."""
        campaign = campaign_service.create_campaign(name="Test")
        campaign_id = campaign.data["id"]

        task = task_service.create_task(title="Task", campaign_id=campaign_id)
        task_id = task.data["id"]

        # Try to add self as dependency
        result = task_service.update_task(
            task_id,
            add_dependencies=[task_id],
        )

        assert result.is_failure
        assert "itself" in result.error_message.lower()
