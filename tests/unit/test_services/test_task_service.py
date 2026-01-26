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
