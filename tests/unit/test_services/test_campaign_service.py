"""Tests for campaign service."""


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
