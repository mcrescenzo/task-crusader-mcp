"""Tests for campaign service."""

from task_crusade_mcp.domain.entities.campaign_spec import CampaignSpec


class TestCampaignService:
    """Tests for CampaignService."""

    def test_create_campaign(self, campaign_service):
        """Test creating a campaign."""
        result = campaign_service.create_campaign(
            name="Test Campaign",
            description="A test campaign",
            priority="high",
        )

        assert result.is_success
        assert result.data["name"] == "Test Campaign"
        assert result.data["description"] == "A test campaign"
        assert result.data["priority"] == "high"
        assert result.data["status"] == "planning"
        assert "id" in result.data

    def test_create_duplicate_campaign(self, campaign_service):
        """Test creating a duplicate campaign fails."""
        campaign_service.create_campaign(name="Unique Name")
        result = campaign_service.create_campaign(name="Unique Name")

        assert result.is_failure
        assert "already exists" in result.error_message.lower()

    def test_get_campaign(self, campaign_service):
        """Test getting a campaign."""
        create_result = campaign_service.create_campaign(name="Test")
        campaign_id = create_result.data["id"]

        result = campaign_service.get_campaign(campaign_id)

        assert result.is_success
        assert result.data["id"] == campaign_id
        assert result.data["name"] == "Test"

    def test_get_nonexistent_campaign(self, campaign_service):
        """Test getting a nonexistent campaign."""
        result = campaign_service.get_campaign("nonexistent-id")

        assert result.is_failure
        assert "not found" in result.error_message.lower()

    def test_list_campaigns(self, campaign_service):
        """Test listing campaigns."""
        campaign_service.create_campaign(name="Campaign 1")
        campaign_service.create_campaign(name="Campaign 2")

        result = campaign_service.list_campaigns()

        assert result.is_success
        assert len(result.data) >= 2

    def test_update_campaign(self, campaign_service):
        """Test updating a campaign."""
        create_result = campaign_service.create_campaign(name="Original")
        campaign_id = create_result.data["id"]

        result = campaign_service.update_campaign(
            campaign_id,
            name="Updated",
            status="active",
        )

        assert result.is_success
        assert result.data["name"] == "Updated"
        assert result.data["status"] == "active"

    def test_delete_campaign(self, campaign_service):
        """Test deleting a campaign."""
        create_result = campaign_service.create_campaign(name="To Delete")
        campaign_id = create_result.data["id"]

        result = campaign_service.delete_campaign(campaign_id)

        assert result.is_success

        # Verify deletion
        get_result = campaign_service.get_campaign(campaign_id)
        assert get_result.is_failure

    def test_get_progress_summary(self, campaign_service, task_service):
        """Test getting campaign progress summary."""
        # Create campaign
        create_result = campaign_service.create_campaign(name="Progress Test")
        campaign_id = create_result.data["id"]

        # Create tasks
        task_service.create_task(title="Task 1", campaign_id=campaign_id)
        task_service.create_task(title="Task 2", campaign_id=campaign_id)

        result = campaign_service.get_progress_summary(campaign_id)

        assert result.is_success
        assert result.data["total_tasks"] == 2
        assert result.data["completion_rate"] == 0.0


class TestCreateCampaignWithTasks:
    """Tests for create_campaign_with_tasks method."""

    def test_create_campaign_with_tasks_basic(self, campaign_service):
        """Test creating campaign with tasks in a single call."""
        spec = CampaignSpec.from_dict({
            "campaign": {
                "name": "Test Project",
                "description": "A test project",
                "priority": "high",
            },
            "tasks": [
                {"temp_id": "t1", "title": "Task 1"},
                {"temp_id": "t2", "title": "Task 2"},
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert result.data["campaign"]["name"] == "Test Project"
        assert len(result.data["tasks"]) == 2
        assert "temp_id_to_uuid" in result.data
        assert "t1" in result.data["temp_id_to_uuid"]
        assert "t2" in result.data["temp_id_to_uuid"]

    def test_create_campaign_with_dependencies(self, campaign_service):
        """Test creating campaign with task dependencies."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Dependency Project"},
            "tasks": [
                {"temp_id": "t1", "title": "First Task"},
                {"temp_id": "t2", "title": "Second Task", "dependencies": ["t1"]},
                {
                    "temp_id": "t3",
                    "title": "Third Task",
                    "dependencies": ["t1", "t2"],
                },
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert len(result.data["tasks"]) == 3

        # Verify dependencies were resolved to UUIDs
        mapping = result.data["temp_id_to_uuid"]
        t3_data = next(t for t in result.data["tasks"] if t["temp_id"] == "t3")
        assert mapping["t1"] in t3_data["dependencies"]
        assert mapping["t2"] in t3_data["dependencies"]

    def test_create_campaign_with_acceptance_criteria(self, campaign_service):
        """Test creating campaign with task acceptance criteria."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Criteria Project"},
            "tasks": [
                {
                    "temp_id": "t1",
                    "title": "Task with criteria",
                    "acceptance_criteria": [
                        "Criterion 1",
                        "Criterion 2",
                    ],
                },
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert result.data["summary"]["with_criteria"] == 1
        task = result.data["tasks"][0]
        assert "acceptance_criteria_details" in task
        assert len(task["acceptance_criteria_details"]) == 2

    def test_create_campaign_with_research(self, campaign_service):
        """Test creating campaign with task research items."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Research Project"},
            "tasks": [
                {
                    "temp_id": "t1",
                    "title": "Task with research",
                    "research": [
                        {"content": "Research finding", "type": "findings"},
                    ],
                },
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert result.data["summary"]["with_research"] == 1
        task = result.data["tasks"][0]
        assert "research" in task
        assert len(task["research"]) == 1

    def test_create_campaign_fails_on_cycle(self, campaign_service):
        """Test that circular dependencies are rejected."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Cyclic Project"},
            "tasks": [
                {"temp_id": "t1", "title": "Task 1", "dependencies": ["t2"]},
                {"temp_id": "t2", "title": "Task 2", "dependencies": ["t1"]},
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_failure
        # Error details contain the specific cycle information
        errors = result.error_details.get("errors", []) if result.error_details else []
        assert any("Circular dependency" in err for err in errors)

    def test_create_campaign_fails_on_invalid_reference(self, campaign_service):
        """Test that invalid dependency references are rejected."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Invalid Ref Project"},
            "tasks": [
                {"temp_id": "t1", "title": "Task 1"},
                {
                    "temp_id": "t2",
                    "title": "Task 2",
                    "dependencies": ["nonexistent"],
                },
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_failure
        # Error details contain the specific reference error
        errors = result.error_details.get("errors", []) if result.error_details else []
        assert any("doesn't exist" in err for err in errors)

    def test_create_campaign_with_no_tasks(self, campaign_service):
        """Test creating campaign with no tasks."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Empty Project"},
            "tasks": [],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert len(result.data["tasks"]) == 0
        assert result.data["summary"]["total_tasks"] == 0

    def test_create_campaign_includes_hints(self, campaign_service):
        """Test that hints are included in the response."""
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Hint Project"},
            "tasks": [
                {"temp_id": "t1", "title": "Task 1"},
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert "hints" in result.data
        assert "next_action" in result.data

    def test_create_campaign_complex_diamond_deps(self, campaign_service):
        """Test complex diamond dependency pattern."""
        #     t1
        #    /  \
        #   t2  t3
        #    \  /
        #     t4
        spec = CampaignSpec.from_dict({
            "campaign": {"name": "Diamond Project"},
            "tasks": [
                {"temp_id": "t1", "title": "Root Task"},
                {"temp_id": "t2", "title": "Branch A", "dependencies": ["t1"]},
                {"temp_id": "t3", "title": "Branch B", "dependencies": ["t1"]},
                {
                    "temp_id": "t4",
                    "title": "Merge Task",
                    "dependencies": ["t2", "t3"],
                },
            ],
        })

        result = campaign_service.create_campaign_with_tasks(spec)

        assert result.is_success
        assert len(result.data["tasks"]) == 4

        # Verify all dependencies were mapped correctly
        mapping = result.data["temp_id_to_uuid"]
        t4_data = next(t for t in result.data["tasks"] if t["temp_id"] == "t4")
        assert len(t4_data["dependencies"]) == 2
        assert mapping["t2"] in t4_data["dependencies"]
        assert mapping["t3"] in t4_data["dependencies"]
