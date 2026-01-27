"""Campaign list widget for the TUI Campaign Browser pane.

This module provides the CampaignListWidget that displays campaigns in a
ListView with filtering, search, and delete capabilities.

Example usage:
    campaign_list = CampaignListWidget(data_service=data_service)
    await campaign_list.load_campaigns()
"""

import logging
from typing import Any, Optional

from rich.text import Text
from textual import on
from textual.message import Message
from textual.widgets import Input, Label, ListItem, ListView

from task_crusade_mcp.tui.constants import (
    CAMPAIGN_STATUS_COLORS,
    CAMPAIGN_STATUS_FILTER_OPTIONS,
    CAMPAIGN_STATUS_ICONS,
)
from task_crusade_mcp.tui.exceptions import DataFetchError
from task_crusade_mcp.tui.services.config_service import TUIConfigService
from task_crusade_mcp.tui.services.data_service import TUIDataService

logger = logging.getLogger(__name__)


class CampaignListItem(ListItem):
    """List item representing a campaign with progress indicator.

    Attributes:
        campaign_id: UUID of the campaign.
    """

    def __init__(
        self,
        campaign_id: str,
        content: Text,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the campaign list item.

        Args:
            campaign_id: UUID of the campaign.
            content: Rich Text content for display.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(Label(content), name=name, id=id, classes=classes)
        self.campaign_id = campaign_id


class CampaignListWidget(ListView):
    """Campaign list widget displaying campaigns with progress indicators.

    This widget extends Textual's ListView to display campaigns with:
    - Campaign name
    - Progress indicator (done/total tasks)
    - Status icon and coloring
    - Filtering by status
    - Search filtering
    - Delete capability

    Keyboard Navigation:
        - j: Move cursor down
        - k: Move cursor up
        - g: Move to first item
        - G: Move to last item
        - f: Cycle status filter
        - /: Open search
        - d: Delete selected campaign

    Messages:
        - CampaignSelected: Emitted when a campaign is selected
        - CampaignDeleted: Emitted when a campaign is deleted
        - CampaignFilterChanged: Emitted when the filter changes
    """

    class CampaignSelected(Message):
        """Message emitted when a campaign is selected.

        Attributes:
            campaign_id: UUID of the selected campaign.
        """

        def __init__(self, campaign_id: str) -> None:
            super().__init__()
            self.campaign_id = campaign_id

    class CampaignDeleted(Message):
        """Message emitted when a campaign is deleted.

        Attributes:
            campaign_id: UUID of the deleted campaign.
        """

        def __init__(self, campaign_id: str) -> None:
            super().__init__()
            self.campaign_id = campaign_id

    class CampaignFilterChanged(Message):
        """Message emitted when the campaign filter changes.

        Attributes:
            filter_value: The new filter value.
            filter_label: Display label for the filter.
        """

        def __init__(self, filter_value: str, filter_label: str) -> None:
            super().__init__()
            self.filter_value = filter_value
            self.filter_label = filter_label

    class CampaignSearchChanged(Message):
        """Message emitted when the campaign search filter changes.

        Attributes:
            query: The current search query string.
            is_active: Whether search filter is currently active.
        """

        def __init__(self, query: str, is_active: bool) -> None:
            super().__init__()
            self.query = query
            self.is_active = is_active

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("g", "first", "First"),
        ("G", "last", "Last"),
        ("f", "cycle_filter", "Filter"),
        ("slash", "open_search", "Search"),
        ("ctrl+l", "clear_search", "Clear Search"),
        ("d", "delete_campaign", "Delete"),
    ]

    def __init__(
        self,
        *,
        data_service: Optional[TUIDataService] = None,
        config_service: Optional[TUIConfigService] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the campaign list widget.

        Args:
            data_service: Optional TUIDataService instance.
            config_service: Optional TUIConfigService instance.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
            disabled: Whether widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.data_service = data_service or TUIDataService()
        self._config_service = config_service or TUIConfigService()

        # Internal storage
        self._all_campaigns: list[dict[str, Any]] = []
        self._filtered_campaigns: list[dict[str, Any]] = []

        # Filter state
        saved_filter = self._config_service.get_campaign_filter()
        self._status_filter: str = saved_filter
        self._search_query: str = ""
        self._search_active: bool = False

        # Loading state
        self._is_loading: bool = False

    @property
    def status_filter(self) -> str:
        """Get the current status filter value."""
        return self._status_filter

    async def load_campaigns(self) -> None:
        """Load campaigns from the data service and display them."""
        self._is_loading = True
        await self._show_loading()

        try:
            self._all_campaigns = await self.data_service.get_campaigns(status=self._status_filter)
            self._filtered_campaigns = self._all_campaigns.copy()
            await self._render_campaigns()

        except DataFetchError as e:
            logger.error(f"Failed to load campaigns: {e}")
            self.notify(str(e), severity="error")
            self._all_campaigns = []
            self._filtered_campaigns = []
            await self._show_empty_state()

        finally:
            self._is_loading = False

    async def refresh_campaigns(self) -> None:
        """Refresh the campaign list by reloading data."""
        await self.load_campaigns()

    async def _show_loading(self) -> None:
        """Display loading indicator."""
        await self.clear()
        await self.append(
            ListItem(Label(Text("Loading campaigns...", style="dim")), id="loading-item")
        )

    async def _show_empty_state(self) -> None:
        """Display empty state message."""
        await self.clear()

        if self._status_filter == "all":
            message = "No campaigns found\n\nUse CLI to create:\ncrusader campaign create"
        else:
            filter_label = next(
                (
                    label
                    for label, value in CAMPAIGN_STATUS_FILTER_OPTIONS
                    if value == self._status_filter
                ),
                self._status_filter,
            )
            message = f"No {filter_label.lower()} campaigns\n\nTry a different filter"

        await self.append(ListItem(Label(Text(message, style="dim")), id="empty-item"))

    async def _render_campaigns(self) -> None:
        """Render the campaign list."""
        await self.clear()

        if not self._filtered_campaigns:
            await self._show_empty_state()
            return

        for campaign in self._filtered_campaigns:
            campaign_id = campaign.get("id", "")
            name = campaign.get("name", "Unnamed Campaign")
            status = campaign.get("status", "planning")
            task_count = campaign.get("task_count", 0)
            done_count = campaign.get("done_count", 0)

            # Get status icon and color
            status_icon = CAMPAIGN_STATUS_ICONS.get(status, "○")
            status_color = CAMPAIGN_STATUS_COLORS.get(status, "dim")

            # Build display text
            display_text = Text()
            display_text.append(f"{status_icon} ", style=status_color)
            display_text.append(name[:30], style=status_color)

            # Progress indicator
            if task_count > 0:
                display_text.append(f" ({done_count}/{task_count})", style="dim")

            await self.append(CampaignListItem(campaign_id=campaign_id, content=display_text))

    def _apply_filters(self) -> list[dict[str, Any]]:
        """Apply all filters to campaigns."""
        filtered = self._all_campaigns.copy()

        # Apply search filter
        if self._search_query:
            query_lower = self._search_query.lower()
            filtered = [c for c in filtered if query_lower in c.get("name", "").lower()]

        return filtered

    async def _refresh_display(self) -> None:
        """Refresh display after filter changes."""
        self._filtered_campaigns = self._apply_filters()
        await self._render_campaigns()

    def get_selected_campaign_id(self) -> Optional[str]:
        """Get the ID of the currently selected campaign."""
        if self.index is None or self.index < 0:
            return None

        try:
            item = self.children[self.index]
            if isinstance(item, CampaignListItem):
                return item.campaign_id
        except (IndexError, AttributeError):
            pass

        return None

    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle campaign selection."""
        if isinstance(event.item, CampaignListItem):
            self.post_message(self.CampaignSelected(event.item.campaign_id))

    async def action_cycle_filter(self) -> None:
        """Cycle through campaign status filters."""
        filter_values = [opt[1] for opt in CAMPAIGN_STATUS_FILTER_OPTIONS]
        current_index = (
            filter_values.index(self._status_filter) if self._status_filter in filter_values else 0
        )

        next_index = (current_index + 1) % len(filter_values)
        new_filter = filter_values[next_index]
        new_label = CAMPAIGN_STATUS_FILTER_OPTIONS[next_index][0]

        self._status_filter = new_filter
        self._config_service.set_campaign_filter(new_filter)

        # Reload campaigns with new filter
        await self.load_campaigns()

        self.post_message(self.CampaignFilterChanged(new_filter, new_label))
        self.notify(f"Filter: {new_label}", severity="information", timeout=1.5)

    async def action_open_search(self) -> None:
        """Open search input."""
        if self._search_active:
            return

        self._search_active = True

        search_input = Input(
            placeholder="Search campaigns...",
            id="campaign-search-input",
            classes="campaign-search-input",
        )
        await self.mount(search_input, before=0)
        search_input.focus()

    async def _close_search(self, clear_filter: bool = False) -> None:
        """Close search input."""
        if not self._search_active:
            return

        self._search_active = False

        try:
            search_input = self.query_one("#campaign-search-input", Input)
            await search_input.remove()
        except Exception:
            pass

        if clear_filter:
            self._search_query = ""
            await self._refresh_display()

        self.focus()

    @on(Input.Changed, "#campaign-search-input")
    async def on_search_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self._search_query = event.value
        await self._refresh_display()
        self.post_message(self.CampaignSearchChanged(self._search_query, bool(self._search_query)))

    @on(Input.Submitted, "#campaign-search-input")
    async def on_search_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        await self._close_search(clear_filter=False)

    async def on_key(self, event) -> None:
        """Handle key events for search escape."""
        if getattr(self, "_search_active", False) and event.key == "escape":
            event.stop()
            # Escape closes the search input but keeps the filter active
            await self._close_search(clear_filter=False)

    async def action_clear_search(self) -> None:
        """Clear the search filter and reset the display."""
        # Close the search input if it's open
        if self._search_active:
            await self._close_search(clear_filter=True)
            self.notify("Search cleared", severity="information", timeout=1.5)
            return

        if not self._search_query:
            return

        self._search_query = ""
        await self._refresh_display()
        self.post_message(self.CampaignSearchChanged("", False))
        self.notify("Search cleared", severity="information", timeout=1.5)

    async def action_delete_campaign(self) -> None:
        """Request deletion of selected campaign."""
        campaign_id = self.get_selected_campaign_id()
        if not campaign_id:
            return

        # Get campaign info for modal
        campaign = next(
            (c for c in self._all_campaigns if c.get("id") == campaign_id),
            None,
        )
        if not campaign:
            return

        from task_crusade_mcp.tui.widgets.delete_modal import DeleteModal

        # Get task count for confirmation
        task_count = await self.data_service.get_campaign_task_count(campaign_id)

        modal = DeleteModal(
            item_type="campaign",
            item_id=campaign_id,
            item_name=campaign.get("name", "Unknown"),
            counts={"tasks": task_count},
        )

        await self.app.push_screen(modal, callback=self._handle_delete_result)

    def _handle_delete_result(
        self, result: tuple[bool, str | None, str | None] | bool | None
    ) -> None:
        """Handle delete modal result."""
        if not isinstance(result, tuple) or not result[0]:
            return

        _, item_type, item_id = result
        if item_type == "campaign" and item_id:
            self.app.call_later(self._perform_delete, item_id)

    async def _perform_delete(self, campaign_id: str) -> None:
        """Perform the campaign deletion."""
        try:
            await self.data_service.delete_campaign(campaign_id)
            self.notify("Campaign deleted", severity="information")
            self.post_message(self.CampaignDeleted(campaign_id))
            await self.refresh_campaigns()

        except Exception as e:
            logger.error(f"Failed to delete campaign: {e}")
            self.notify(f"Delete failed: {e}", severity="error")
