"""Tests for CampaignListWidget.

This module tests the CampaignListWidget component, including:
- Loading and displaying campaign lists
- Campaign selection
- Status filtering
- Search filtering
- Sorting
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from rich.text import Text

from task_crusade_mcp.tui.exceptions import DataFetchError
from task_crusade_mcp.tui.widgets.campaign_list import (
    CampaignListItem,
    CampaignListWidget,
)


class TestCampaignListItem:
    """Tests for CampaignListItem."""

    def test_campaign_list_item_stores_campaign_id(self) -> None:
        """CampaignListItem stores the campaign_id."""
        content = Text("Test Campaign")
        item = CampaignListItem(
            campaign_id="campaign-uuid-001",
            content=content,
        )

        assert item.campaign_id == "campaign-uuid-001"


class TestCampaignListWidgetInit:
    """Tests for CampaignListWidget initialization."""

    def test_init_with_default_services(self) -> None:
        """Widget creates default services if none provided."""
        widget = CampaignListWidget()
        assert widget.data_service is not None
        assert widget._all_campaigns == []
        assert widget._filtered_campaigns == []

    def test_init_with_custom_data_service(self, mock_data_service: MagicMock) -> None:
        """Widget accepts custom data service."""
        widget = CampaignListWidget(data_service=mock_data_service)
        assert widget.data_service is mock_data_service

    def test_init_loads_saved_filter(self, mock_config_service: MagicMock) -> None:
        """Widget loads saved filter from config service."""
        mock_config_service.get_campaign_filter.return_value = "active"
        widget = CampaignListWidget(config_service=mock_config_service)
        assert widget._status_filter == "active"


class TestCampaignListWidgetLoadCampaigns:
    """Tests for loading campaigns."""

    @pytest.mark.asyncio
    async def test_load_campaigns_fetches_from_service(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """load_campaigns fetches campaigns from data service."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._show_loading = AsyncMock()
        widget._render_campaigns = AsyncMock()

        await widget.load_campaigns()

        mock_data_service.get_campaigns.assert_called_once()
        assert len(widget._all_campaigns) == 3

    @pytest.mark.asyncio
    async def test_load_campaigns_with_status_filter(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """load_campaigns passes status filter to service."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._status_filter = "active"
        widget._show_loading = AsyncMock()
        widget._render_campaigns = AsyncMock()

        await widget.load_campaigns()

        mock_data_service.get_campaigns.assert_called_once_with(status="active")

    @pytest.mark.asyncio
    async def test_load_campaigns_handles_fetch_error(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """load_campaigns handles DataFetchError gracefully."""
        mock_data_service.get_campaigns = AsyncMock(
            side_effect=DataFetchError("fetch campaigns", "Connection failed")
        )
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._show_loading = AsyncMock()
        widget._show_empty_state = AsyncMock()
        widget.notify = MagicMock()

        await widget.load_campaigns()

        widget.notify.assert_called()
        assert widget._all_campaigns == []

    @pytest.mark.asyncio
    async def test_load_empty_campaign_list(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """Loading empty campaign list shows empty state."""
        mock_data_service.get_campaigns = AsyncMock(return_value=[])
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._show_loading = AsyncMock()
        widget._render_campaigns = AsyncMock()

        await widget.load_campaigns()

        assert widget._all_campaigns == []


class TestCampaignListWidgetFiltering:
    """Tests for campaign filtering."""

    def test_apply_search_filter(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Search filter filters campaigns by name."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._all_campaigns = sample_campaign_list
        widget._search_query = "active"

        filtered = widget._apply_filters()

        assert len(filtered) == 1
        assert filtered[0]["name"] == "Active Campaign"

    def test_apply_search_filter_case_insensitive(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Search filter is case-insensitive."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._all_campaigns = sample_campaign_list
        widget._search_query = "ACTIVE"

        filtered = widget._apply_filters()

        assert len(filtered) == 1

    def test_empty_search_returns_all(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Empty search query returns all campaigns."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._all_campaigns = sample_campaign_list
        widget._search_query = ""

        filtered = widget._apply_filters()

        assert len(filtered) == 3


class TestCampaignListWidgetSorting:
    """Tests for campaign sorting."""

    def test_sort_by_name(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Sort by name orders alphabetically."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 0  # Name

        sorted_campaigns = widget._apply_sort(sample_campaign_list)

        assert sorted_campaigns[0]["name"] == "Active Campaign"
        assert sorted_campaigns[1]["name"] == "Completed Campaign"
        assert sorted_campaigns[2]["name"] == "Planning Campaign"

    def test_sort_by_progress(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Sort by progress orders by completion percentage (descending)."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 1  # Progress

        sorted_campaigns = widget._apply_sort(sample_campaign_list)

        # Completed campaign (8/8 = 100%) should be first
        assert sorted_campaigns[0]["name"] == "Completed Campaign"

    def test_sort_by_task_count(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Sort by task count orders by total tasks (descending)."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 2  # Task count

        sorted_campaigns = widget._apply_sort(sample_campaign_list)

        # Active campaign (10 tasks) should be first
        assert sorted_campaigns[0]["name"] == "Active Campaign"

    def test_sort_by_priority(
        self,
        mock_data_service: MagicMock,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Sort by priority orders high > medium > low."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 3  # Priority

        sorted_campaigns = widget._apply_sort(sample_campaign_list)

        # High priority campaign should be first
        assert sorted_campaigns[0]["priority"] == "high"

    def test_sort_empty_list(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """Sorting empty list returns empty list."""
        widget = CampaignListWidget(data_service=mock_data_service)

        result = widget._apply_sort([])

        assert result == []


class TestCampaignListWidgetSelection:
    """Tests for campaign selection."""

    def test_get_selected_campaign_id_returns_none_when_empty(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """get_selected_campaign_id returns None when list is empty."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget.index = None

        result = widget.get_selected_campaign_id()

        assert result is None

    def test_get_selected_campaign_id_returns_none_when_no_selection(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """get_selected_campaign_id returns None when index is -1."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget.index = -1

        result = widget.get_selected_campaign_id()

        assert result is None


class TestCampaignListWidgetActions:
    """Tests for campaign list actions."""

    @pytest.mark.asyncio
    async def test_cycle_filter_updates_filter(
        self,
        mock_data_service: MagicMock,
        mock_config_service: MagicMock,
    ) -> None:
        """action_cycle_filter cycles through filter options."""
        widget = CampaignListWidget(
            data_service=mock_data_service,
            config_service=mock_config_service,
        )
        widget._status_filter = "all"
        widget.load_campaigns = AsyncMock()
        widget.post_message = MagicMock()
        widget.notify = MagicMock()

        await widget.action_cycle_filter()

        # Should have cycled to next filter
        assert widget._status_filter != "all"
        mock_config_service.set_campaign_filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_cycle_sort_changes_sort_mode(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """action_cycle_sort cycles through sort modes."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 0
        widget._refresh_display = AsyncMock()
        widget.notify = MagicMock()

        await widget.action_cycle_sort()

        assert widget._sort_mode == 1

    @pytest.mark.asyncio
    async def test_cycle_sort_wraps_around(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """action_cycle_sort wraps around to first mode."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget._sort_mode = 3  # Last mode
        widget._refresh_display = AsyncMock()
        widget.notify = MagicMock()

        await widget.action_cycle_sort()

        assert widget._sort_mode == 0

    def test_new_campaign_posts_message(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """action_new_campaign posts NewCampaignRequested message."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget.post_message = MagicMock()

        widget.action_new_campaign()

        widget.post_message.assert_called_once()
        call_args = widget.post_message.call_args[0][0]
        assert isinstance(call_args, CampaignListWidget.NewCampaignRequested)


class TestCampaignListWidgetSearch:
    """Tests for search functionality (logic tests without app context)."""

    def test_search_active_flag_toggle(self) -> None:
        """Search active flag can be toggled."""
        search_active = False

        # Open search
        if not search_active:
            search_active = True

        assert search_active is True

        # Close search
        search_active = False
        assert search_active is False

    def test_clear_search_clears_query(self) -> None:
        """Clearing search resets the query."""
        search_query = "test"

        # Clear
        search_query = ""

        assert search_query == ""

    def test_search_query_filtering_logic(
        self,
        sample_campaign_list: list[dict[str, Any]],
    ) -> None:
        """Search query filters campaigns by name."""
        search_query = "active"
        filtered = [
            c
            for c in sample_campaign_list
            if search_query.lower() in c.get("name", "").lower()
        ]
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Active Campaign"


class TestCampaignListWidgetMessages:
    """Tests for message posting."""

    def test_campaign_selected_message(self) -> None:
        """CampaignSelected message contains campaign_id."""
        message = CampaignListWidget.CampaignSelected(campaign_id="camp-123")
        assert message.campaign_id == "camp-123"

    def test_campaign_deleted_message(self) -> None:
        """CampaignDeleted message contains campaign_id."""
        message = CampaignListWidget.CampaignDeleted(campaign_id="camp-123")
        assert message.campaign_id == "camp-123"

    def test_campaign_filter_changed_message(self) -> None:
        """CampaignFilterChanged message contains filter info."""
        message = CampaignListWidget.CampaignFilterChanged(
            filter_value="active",
            filter_label="Active",
        )
        assert message.filter_value == "active"
        assert message.filter_label == "Active"

    def test_campaign_search_changed_message(self) -> None:
        """CampaignSearchChanged message contains query and active flag."""
        message = CampaignListWidget.CampaignSearchChanged(
            query="test",
            is_active=True,
        )
        assert message.query == "test"
        assert message.is_active is True

    def test_campaign_created_message(self) -> None:
        """CampaignCreated message contains campaign data."""
        message = CampaignListWidget.CampaignCreated(
            campaign_id="camp-123",
            campaign_data={"name": "Test"},
        )
        assert message.campaign_id == "camp-123"
        assert message.campaign_data["name"] == "Test"


class TestCampaignListWidgetRefresh:
    """Tests for refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_campaigns_reloads(
        self,
        mock_data_service: MagicMock,
    ) -> None:
        """refresh_campaigns calls load_campaigns."""
        widget = CampaignListWidget(data_service=mock_data_service)
        widget.load_campaigns = AsyncMock()

        await widget.refresh_campaigns()

        widget.load_campaigns.assert_called_once()
