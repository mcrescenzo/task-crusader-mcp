"""Campaign and Task pane for the TUI application.

This module provides the CampaignTaskPane class that composes the three main widgets
(CampaignListWidget, TaskDataTable, TaskDetailWidget) into a 3-pane horizontal
layout with Tab navigation between panes and coordinated data flow.

Example usage:
    from task_crusade_mcp.tui.screens.main import CampaignTaskPane

    class CrusaderTUI(App):
        def compose(self):
            yield CampaignTaskPane(data_service=self._data_service)
"""

import logging

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.widgets import Static

from task_crusade_mcp.tui.services.config_service import TUIConfigService
from task_crusade_mcp.tui.services.data_service import TUIDataService
from task_crusade_mcp.tui.widgets import (
    CampaignListWidget,
    TaskDataTable,
    TaskDetailWidget,
)

logger = logging.getLogger(__name__)


class CampaignTaskPane(Vertical):
    """3-pane widget for campaign and task management.

    Keyboard navigation:
    - Tab: Cycle focus forward (campaigns -> tasks -> detail -> campaigns)
    - Shift+Tab: Cycle focus backward
    - r: Refresh data

    Data flow:
    - Campaign selection triggers task list update
    - Task selection triggers detail panel update
    """

    MIN_WIDTH = 80
    MIN_HEIGHT = 24

    BREAKPOINT_SMALL = 100
    BREAKPOINT_MEDIUM = 140

    BINDINGS = [
        Binding("tab", "focus_next_pane", "Next Pane", show=True),
        Binding("shift+tab", "focus_previous_pane", "Prev Pane", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(
        self,
        data_service: TUIDataService | None = None,
        config_service: TUIConfigService | None = None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the campaign/task pane.

        Args:
            data_service: Optional shared TUIDataService instance.
            config_service: Optional shared TUIConfigService instance.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self.data_service = data_service or TUIDataService()
        self._config_service = config_service or TUIConfigService()
        self._panes: list[CampaignListWidget | TaskDataTable | TaskDetailWidget] = []
        self._current_pane_index = 0
        self._current_width: int = 80
        self._current_height: int = 24
        self._detail_collapsed: bool = False
        self._last_selected_campaign_id: str | None = None
        self._last_selected_task_id: str | None = None
        self._last_focused_pane_index: int = -1
        self._suppress_task_selection: bool = False

    def compose(self) -> ComposeResult:
        """Compose the pane layout with 3-pane content."""
        yield Static("", id="size-warning")

        with Horizontal(id="pane-container"):
            with Vertical(id="campaign-pane"):
                yield Static("CAMPAIGNS", id="campaign-pane-header")
                yield CampaignListWidget(
                    data_service=self.data_service,
                    id="campaign-list",
                    classes="pane-content",
                )

            with Vertical(id="task-pane"):
                yield Static("TASKS", id="task-pane-header")
                yield TaskDataTable(
                    data_service=self.data_service,
                    config_service=self._config_service,
                    id="task-list",
                    classes="pane-content",
                )

            with Vertical(id="detail-pane"):
                yield Static("DETAILS", id="detail-pane-header")
                yield TaskDetailWidget(
                    data_service=self.data_service,
                    id="task-detail",
                    classes="pane-content",
                )

    async def on_mount(self) -> None:
        """Handle screen mount - load initial data and set up pane tracking."""
        campaign_list = self.query_one("#campaign-list", CampaignListWidget)
        task_list = self.query_one("#task-list", TaskDataTable)
        task_detail = self.query_one("#task-detail", TaskDetailWidget)

        self._panes = [campaign_list, task_list, task_detail]
        self._current_pane_index = 0

        campaign_list.focus()

        self._update_campaign_header(campaign_list.status_filter)
        self._update_task_header(task_list.status_filter)

        await campaign_list.load_campaigns()

        self._apply_responsive_layout()

    def _get_filter_label(self, filter_value: str, options: list[tuple[str, str]]) -> str:
        """Get the display label for a filter value."""
        for label, value in options:
            if value == filter_value:
                return label
        return filter_value.title()

    def _update_campaign_header(self, filter_value: str) -> None:
        """Update the campaign pane header to show current filter."""
        from task_crusade_mcp.tui.constants import CAMPAIGN_STATUS_FILTER_OPTIONS

        try:
            header = self.query_one("#campaign-pane-header", Static)
            label = self._get_filter_label(filter_value, CAMPAIGN_STATUS_FILTER_OPTIONS)
            header.update(f"CAMPAIGNS ({label})")
        except Exception:
            pass

    def _update_task_header(self, filter_value: str) -> None:
        """Update the task pane header to show current filter."""
        from task_crusade_mcp.tui.constants import STATUS_FILTER_OPTIONS

        try:
            header = self.query_one("#task-pane-header", Static)
            label = self._get_filter_label(filter_value, STATUS_FILTER_OPTIONS)
            header.update(f"TASKS ({label})")
        except Exception:
            pass

    def _update_detail_header(self, title: str) -> None:
        """Update the detail pane header text."""
        try:
            header = self.query_one("#detail-pane-header", Static)
            header.update(title)
        except Exception:
            pass

    @on(CampaignListWidget.CampaignFilterChanged)
    def on_campaign_filter_changed(self, event: CampaignListWidget.CampaignFilterChanged) -> None:
        """Handle campaign filter change - update pane header."""
        self._update_campaign_header(event.filter_value)

    @on(TaskDataTable.TaskFilterChanged)
    def on_task_data_table_task_filter_changed(
        self, event: TaskDataTable.TaskFilterChanged
    ) -> None:
        """Handle task filter change - update pane header."""
        self._update_task_header(event.filter_value)

    def on_resize(self, event: Resize) -> None:
        """Handle terminal resize events for responsive layout."""
        self._current_width = event.size.width
        self._current_height = event.size.height
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Apply responsive layout based on current terminal size."""
        try:
            campaign_pane = self.query_one("#campaign-pane", Vertical)
            task_pane = self.query_one("#task-pane", Vertical)
            detail_pane = self.query_one("#detail-pane", Vertical)
        except Exception:
            return

        width = self._current_width
        height = self._current_height

        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            self._show_size_warning(width, height)
        else:
            self._hide_size_warning()

        if width < self.BREAKPOINT_SMALL:
            self._set_pane_widths(campaign_pane, task_pane, detail_pane, 20, 40, 40)

            if width < self.MIN_WIDTH:
                self._collapse_detail_pane(detail_pane, task_pane)
            else:
                self._expand_detail_pane(detail_pane)

        elif width < self.BREAKPOINT_MEDIUM:
            self._set_pane_widths(campaign_pane, task_pane, detail_pane, 20, 40, 40)
            self._expand_detail_pane(detail_pane)

        else:
            self._set_pane_widths(campaign_pane, task_pane, detail_pane, 20, 40, 40)
            self._expand_detail_pane(detail_pane)

    def _set_pane_widths(
        self,
        campaign_pane: Vertical,
        task_pane: Vertical,
        detail_pane: Vertical,
        campaign_pct: int,
        task_pct: int,
        detail_pct: int,
    ) -> None:
        """Set pane widths as percentages."""
        campaign_pane.styles.width = f"{campaign_pct}%"
        task_pane.styles.width = f"{task_pct}%"
        detail_pane.styles.width = f"{detail_pct}%"

    def _collapse_detail_pane(self, detail_pane: Vertical, task_pane: Vertical) -> None:
        """Collapse the detail pane for very small terminals."""
        if not self._detail_collapsed:
            self._detail_collapsed = True
            detail_pane.add_class("collapsed")
            task_pane.styles.width = "60%"

    def _expand_detail_pane(self, detail_pane: Vertical) -> None:
        """Expand the detail pane (restore from collapsed state)."""
        if self._detail_collapsed:
            self._detail_collapsed = False
            detail_pane.remove_class("collapsed")

    def _show_size_warning(self, width: int, height: int) -> None:
        """Show a warning when terminal is below minimum size."""
        try:
            warning = self.query_one("#size-warning", Static)
            warning.update(
                f"⚠ Terminal too small ({width}x{height}). "
                f"Minimum: {self.MIN_WIDTH}x{self.MIN_HEIGHT}"
            )
            warning.add_class("visible")
        except Exception:
            pass

    def _hide_size_warning(self) -> None:
        """Hide the size warning banner."""
        try:
            warning = self.query_one("#size-warning", Static)
            warning.remove_class("visible")
        except Exception:
            pass

    def on_campaign_list_widget_campaign_selected(
        self, event: CampaignListWidget.CampaignSelected
    ) -> None:
        """Handle campaign selection - load tasks and show campaign summary."""
        logger.debug(f"[CAMPAIGN SELECTED] campaign_id={event.campaign_id[:8]}...")

        self._last_selected_campaign_id = event.campaign_id
        self._last_selected_task_id = None
        self._suppress_task_selection = True

        task_data_table = self.query_one("#task-list", TaskDataTable)
        self.run_worker(task_data_table.load_tasks(campaign_id=event.campaign_id))

        task_detail = self.query_one("#task-detail", TaskDetailWidget)
        self._update_detail_header("CAMPAIGN DETAILS")
        self.run_worker(task_detail.load_campaign_summary(event.campaign_id))

    def on_task_data_table_task_selected(self, event: TaskDataTable.TaskSelected) -> None:
        """Handle task selection - load details for the selected task."""
        logger.debug(
            f"[TASK SELECTED] task_id={event.task_id[:8]}..., "
            f"suppression={self._suppress_task_selection}"
        )

        if self._suppress_task_selection:
            logger.debug("[TASK SELECTED] Suppressed - clearing flag and returning")
            self._suppress_task_selection = False
            return

        logger.debug(
            "[TASK SELECTED] Processing - setting _last_selected_task_id "
            "and loading task details"
        )

        self._last_selected_task_id = event.task_id

        task_detail = self.query_one("#task-detail", TaskDetailWidget)
        self._update_detail_header("TASK DETAIL")
        self.run_worker(task_detail.load_task(event.task_id))

    def on_campaign_list_widget_campaign_deleted(
        self, _event: CampaignListWidget.CampaignDeleted
    ) -> None:
        """Handle campaign deletion - clear task list and detail panel."""
        self._last_selected_campaign_id = None
        self._last_selected_task_id = None
        self._suppress_task_selection = False

        task_data_table = self.query_one("#task-list", TaskDataTable)
        self.run_worker(task_data_table.clear_tasks())

        task_detail = self.query_one("#task-detail", TaskDetailWidget)
        self._update_detail_header("DETAILS")
        self.run_worker(task_detail.clear_task())

    def _get_focusable_panes(
        self,
    ) -> list[CampaignListWidget | TaskDataTable | TaskDetailWidget]:
        """Get list of currently focusable panes."""
        if self._detail_collapsed:
            return self._panes[:2]
        return self._panes

    def action_focus_next_pane(self) -> None:
        """Cycle focus to the next pane."""
        focusable = self._get_focusable_panes()
        if not focusable:
            return

        if self._current_pane_index >= len(focusable):
            self._current_pane_index = 0

        self._current_pane_index = (self._current_pane_index + 1) % len(focusable)
        focusable[self._current_pane_index].focus()

    def action_focus_previous_pane(self) -> None:
        """Cycle focus to the previous pane."""
        focusable = self._get_focusable_panes()
        if not focusable:
            return

        if self._current_pane_index >= len(focusable):
            self._current_pane_index = len(focusable) - 1

        self._current_pane_index = (self._current_pane_index - 1) % len(focusable)
        focusable[self._current_pane_index].focus()

    async def action_refresh(self) -> None:
        """Refresh all data in the current view."""
        campaign_list = self.query_one("#campaign-list", CampaignListWidget)
        task_data_table = self.query_one("#task-list", TaskDataTable)
        task_detail = self.query_one("#task-detail", TaskDetailWidget)

        selected_campaign_id = campaign_list.get_selected_campaign_id()
        selected_task_id = task_data_table.get_selected_task_id()

        try:
            await campaign_list.refresh_campaigns()

            if selected_campaign_id:
                self._restore_campaign_selection(campaign_list, selected_campaign_id)

            await task_data_table.refresh_tasks()

            if selected_task_id:
                self._restore_task_selection(task_data_table, selected_task_id)

            await task_detail.refresh_task()

            self.notify("Data refreshed")

        except Exception as e:
            self.notify(f"Refresh failed: {e}", severity="error")

    def _restore_campaign_selection(
        self, campaign_list: CampaignListWidget, campaign_id: str
    ) -> None:
        """Attempt to restore campaign selection after refresh."""
        for i, child in enumerate(campaign_list.children):
            if hasattr(child, "campaign_id") and getattr(child, "campaign_id", None) == campaign_id:
                campaign_list.index = i
                return

    def _restore_task_selection(self, task_data_table: TaskDataTable, task_id: str) -> None:
        """Attempt to restore task selection after refresh."""
        try:
            for row_index, row in enumerate(task_data_table.ordered_rows):
                if row.key.value == task_id:
                    task_data_table.move_cursor(row=row_index)
                    return
        except (IndexError, AttributeError):
            pass

    def _update_detail_pane_for_focus(self) -> None:
        """Update detail pane based on currently focused pane."""
        if self._current_pane_index == self._last_focused_pane_index:
            return

        if self._current_pane_index == 2:
            return

        self._last_focused_pane_index = self._current_pane_index

        task_detail = self.query_one("#task-detail", TaskDetailWidget)

        if self._current_pane_index == 0:
            if self._last_selected_campaign_id:
                self._update_detail_header("CAMPAIGN DETAILS")
                self.run_worker(task_detail.load_campaign_summary(self._last_selected_campaign_id))
            else:
                self._update_detail_header("DETAILS")
                self.run_worker(task_detail.clear_task())

        elif self._current_pane_index == 1:
            if self._last_selected_task_id:
                self._update_detail_header("TASK DETAIL")
                self.run_worker(task_detail.load_task(self._last_selected_task_id))
            else:
                self._update_detail_header("DETAILS")
                self.run_worker(task_detail.clear_task())

    def watch_focused(self, _focused: bool) -> None:
        """Track which pane has focus for Tab navigation."""
        if self._panes:
            for i, pane in enumerate(self._panes):
                if pane.has_focus or pane.has_focus_within:
                    self._current_pane_index = i
                    self._update_detail_pane_for_focus()
                    break
