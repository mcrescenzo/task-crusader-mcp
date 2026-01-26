"""Task data table widget for the TUI Task Navigator pane.

This module provides the TaskDataTable widget that displays tasks using Textual's
DataTable for efficient virtualized rendering.

Example usage:
    task_table = TaskDataTable(data_service=data_service)
    await task_table.load_tasks(campaign_id="abc-123")
"""

import logging
from typing import Any, Optional

from rich.text import Text
from textual import on
from textual.message import Message
from textual.widgets import DataTable, Input

from task_crusade_mcp.tui.constants import (
    ACTIONABLE_COLOR,
    ACTIONABLE_ICON,
    PRIORITY_COLORS,
    PRIORITY_ICONS,
    RICH_STATUS_COLORS,
    STATUS_FILTER_OPTIONS,
    STATUS_ICONS,
)
from task_crusade_mcp.tui.exceptions import DataFetchError
from task_crusade_mcp.tui.services.config_service import TUIConfigService
from task_crusade_mcp.tui.services.data_service import TUIDataService

logger = logging.getLogger(__name__)


class TaskDataTable(DataTable):
    """Virtualized task list widget using DataTable for efficient rendering.

    Keyboard Navigation:
        - j: Move cursor down one row
        - k: Move cursor up one row
        - g: Move cursor to first row
        - G: Move cursor to last row
        - v: Toggle selection mode on/off
        - Space: Toggle current row selection (in selection mode)
        - A: Select all visible rows (in selection mode, toggle behavior)

    Messages:
        - TaskSelected: Emitted when the cursor moves to a new row
        - TaskDeleteRequested: Emitted when user requests to delete a task
        - TaskFilterChanged: Emitted when the task status filter changes
    """

    class TaskSelected(Message):
        """Message emitted when a task is selected via cursor movement."""

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    class TaskDeleteRequested(Message):
        """Message emitted when the user requests to delete a task."""

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    class TaskFilterChanged(Message):
        """Message emitted when the task status filter changes."""

        def __init__(self, filter_value: str, filter_label: str) -> None:
            super().__init__()
            self.filter_value = filter_value
            self.filter_label = filter_label

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("g", "scroll_top", "First"),
        ("G", "scroll_bottom", "Last"),
        ("f", "cycle_filter", "Filter"),
        ("a", "toggle_actionable_filter", "Actionable"),
        ("d", "delete_task", "Delete"),
        ("slash", "open_search", "Search"),
        ("v", "toggle_selection_mode", "Selection Mode"),
        ("space", "toggle_selection", "Toggle Selection"),
        ("A", "select_all_visible", "Select All"),
        ("b", "open_bulk_actions", "Bulk Actions"),
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
        """Initialize the TaskDataTable widget."""
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            cursor_type="row",
            zebra_stripes=True,
        )

        self.data_service = data_service or TUIDataService()
        self._config_service = config_service or TUIConfigService()

        # Configure columns
        self.add_column("#", width=4, key="order")
        self.add_column("Task", width=None, key="task")
        self.add_column("Pri", width=3, key="priority")

        # Internal storage
        self._all_tasks: list[dict[str, Any]] = []
        self._filtered_tasks: list[dict[str, Any]] = []

        # Campaign tracking
        self._campaign_id: Optional[str] = None

        # Loading state
        self._is_loading = False

        # Filter state
        saved_filter = self._config_service.get_status_filter()
        self._status_filter: str = saved_filter
        self._search_query: str = ""
        self._show_actionable_only: bool = False

        # Search UI state
        self._search_active: bool = False

        # Selection mode state
        self._selection_mode: bool = False
        self._selected_keys: set[str] = set()

    @property
    def status_filter(self) -> str:
        """Get the current status filter value."""
        return self._status_filter

    @staticmethod
    def _render_priority_cell(task: dict[str, Any]) -> Text:
        """Render priority cell with colored icon."""
        priority = task.get("priority", "medium")
        if priority is None:
            priority = "medium"
        priority = priority.lower()

        icon = PRIORITY_ICONS.get(priority, "?")
        color = PRIORITY_COLORS.get(priority, "white")

        return Text(icon, style=color)

    async def load_tasks(
        self,
        campaign_id: Optional[str] = None,
        tasks: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Load tasks into the DataTable."""
        if campaign_id is not None and tasks is not None:
            raise ValueError("Cannot provide both campaign_id and tasks parameters")
        if campaign_id is None and tasks is None:
            raise ValueError("Must provide either campaign_id or tasks parameter")

        if campaign_id is not None:
            self._campaign_id = campaign_id
            self._is_loading = True
            await self._show_loading()

            try:
                fetched_tasks = await self.data_service.get_tasks(campaign_id=campaign_id)
                await self._render_tasks(fetched_tasks)

            except DataFetchError as e:
                logger.error(f"Failed to fetch tasks for campaign {campaign_id}: {e}")
                self.notify(str(e), severity="error")
                self._all_tasks = []
                self._filtered_tasks = []
                await self._show_empty_state()

            finally:
                self._is_loading = False

            return

        if tasks is not None:
            await self._render_tasks(tasks)

    async def _render_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Render tasks into the DataTable."""
        await self._show_loading()

        try:
            self._all_tasks = tasks
            self._filtered_tasks = tasks.copy()
            self._enrich_dependency_details()
            self.clear()

            if not tasks:
                await self._show_empty_state()
                return

            for task in tasks:
                task_id = task.get("id", "")
                priority_order = task.get("priority_order", 0)

                order_str = str(priority_order)
                task_cell = self._render_task_cell(task)
                priority_cell = self._render_priority_cell(task)

                self.add_row(order_str, task_cell, priority_cell, key=task_id)
        finally:
            self._is_loading = False

    async def _show_loading(self) -> None:
        """Display loading indicator."""
        self._is_loading = True
        self.clear()
        loading_row = ("", "Loading tasks...", "")
        self.add_row(*loading_row, key="loading")

    async def _show_empty_state(self) -> None:
        """Display empty state message."""
        self.clear()

        if self._status_filter == "all":
            message = "No tasks found\n\nUse CLI to create:\ncrusader task create"
        else:
            filter_label = next(
                (label for label, value in STATUS_FILTER_OPTIONS if value == self._status_filter),
                self._status_filter,
            )
            message = f"No {filter_label.lower()} tasks found\n\nTry a different filter"

        empty_row = ("", message, "")
        self.add_row(*empty_row, key="empty")

    def _enrich_dependency_details(self) -> None:
        """Enrich tasks with dependency details for display."""
        task_map = {task["id"]: task for task in self._all_tasks}

        for task in self._all_tasks:
            dependencies = task.get("dependencies", [])
            if dependencies:
                dep_details = []
                for dep_id in dependencies:
                    if dep_id in task_map:
                        dep_task = task_map[dep_id]
                        dep_details.append(
                            {
                                "id": dep_id,
                                "priority_order": dep_task.get("priority_order", "?"),
                                "status": dep_task.get("status", "unknown"),
                            }
                        )
                    else:
                        dep_details.append(
                            {
                                "id": dep_id,
                                "priority_order": "?",
                                "status": "unknown",
                            }
                        )
                task["dependency_details"] = dep_details

    def _apply_status_filter(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply status-based filtering."""
        if self._status_filter == "actionable":
            return [
                task
                for task in tasks
                if task.get("status") == "pending" and self._has_no_unmet_dependencies(task)
            ]
        elif self._status_filter != "all":
            return [task for task in tasks if task.get("status") == self._status_filter]

        return tasks

    def _apply_search_filter(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply search query filtering."""
        if not self._search_query:
            return tasks

        query_lower = self._search_query.lower()
        return [task for task in tasks if query_lower in task.get("title", "").lower()]

    def _apply_actionable_filter(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply actionable-only filtering."""
        if not self._show_actionable_only:
            return tasks

        return [
            task
            for task in tasks
            if task.get("status") == "pending" and self._has_no_unmet_dependencies(task)
        ]

    async def _apply_filters(self) -> None:
        """Apply all active filters to tasks and refresh display."""
        filtered = self._all_tasks.copy()
        filtered = self._apply_status_filter(filtered)
        filtered = self._apply_search_filter(filtered)
        filtered = self._apply_actionable_filter(filtered)

        self._filtered_tasks = filtered
        await self._refresh_display(filtered)

    def _has_no_unmet_dependencies(self, task: dict[str, Any]) -> bool:
        """Check if a task has no unmet dependencies."""
        dependencies = task.get("dependencies", [])
        if not dependencies:
            return True

        dep_details = task.get("dependency_details", [])
        if not dep_details:
            return False

        return all(dep.get("status") == "done" for dep in dep_details)

    async def _refresh_display(self, tasks: list[dict[str, Any]]) -> None:
        """Refresh the DataTable display with the given task list."""
        self.clear()

        if not tasks:
            await self._show_empty_state()
            return

        for task in tasks:
            task_id = task.get("id", "")
            priority_order = task.get("priority_order", 0)

            order_str = str(priority_order)
            task_cell = self._render_task_cell(task)
            priority_cell = self._render_priority_cell(task)

            self.add_row(order_str, task_cell, priority_cell, key=task_id)

    def get_selected_task_id(self) -> Optional[str]:
        """Get the task_id of the currently selected row."""
        if self.cursor_row < 0 or self.row_count == 0:
            return None

        try:
            row = self.ordered_rows[self.cursor_row]
            task_id = row.key.value

            if task_id in ("loading", "empty"):
                return None

            return task_id
        except (IndexError, AttributeError):
            return None

    def get_task_ids_for_rows(self, row_indices: list[int]) -> list[str]:
        """Get task_ids for a list of row indices."""
        task_ids = []

        for index in row_indices:
            if index < 0 or index >= self.row_count:
                continue

            try:
                row = self.ordered_rows[index]
                task_id = row.key.value

                if task_id not in ("loading", "empty"):
                    task_ids.append(task_id)
            except (IndexError, AttributeError):
                continue

        return task_ids

    async def refresh_tasks(self) -> None:
        """Refresh the task list by reloading data for the current campaign."""
        if self._campaign_id is None:
            return

        await self._show_loading()

        try:
            tasks = await self.data_service.get_tasks(campaign_id=self._campaign_id)
            await self.load_tasks(tasks=tasks)

        except DataFetchError as e:
            logger.error(f"Failed to refresh tasks for campaign {self._campaign_id}: {e}")
            self.notify(str(e), severity="error")
            self._all_tasks = []
            self._filtered_tasks = []
            await self._show_empty_state()
        finally:
            self._is_loading = False

    async def clear_tasks(self) -> None:
        """Clear the task list and reset all state."""
        self._campaign_id = None
        self._all_tasks = []
        self._filtered_tasks = []
        self._status_filter = "all"
        self._search_query = ""
        self._show_actionable_only = False
        self._search_active = False

        self.clear()
        await self._show_empty_state()

    def _render_task_cell(self, task: dict[str, Any]) -> Text:
        """Render task cell with status icon, actionable indicator, title, and dependency warning."""
        task_id = task.get("id", "")
        title = task.get("title", "Unnamed Task")
        status = task.get("status", "")
        has_dependencies = task.get("has_dependencies", False)
        dependency_count = task.get("dependency_count", 0)

        status_icon = STATUS_ICONS.get(status, "?")
        status_color = RICH_STATUS_COLORS.get(status, "dim")

        is_actionable = status == "pending" and self._has_no_unmet_dependencies(task)

        show_warning = (
            has_dependencies and dependency_count > 0 and status == "pending" and not is_actionable
        )

        show_actionable = is_actionable

        components = []

        if self._selection_mode:
            is_selected = task_id in self._selected_keys
            checkbox = "☑" if is_selected else "☐"
            checkbox_color = "green" if is_selected else "dim"
            components.extend([(checkbox, checkbox_color), " "])

        components.extend([(status_icon, status_color), " "])

        if show_actionable:
            components.extend([(ACTIONABLE_ICON, ACTIONABLE_COLOR), " "])

        components.append(title)

        if show_warning:
            components.extend([" ", (f"⚠{dependency_count}", "yellow")])

        return Text.assemble(*components)

    @on(DataTable.RowHighlighted)
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting and emit TaskSelected message."""
        if event.row_key is None:
            return

        task_id = event.row_key.value

        if task_id is None:
            return

        if task_id in ("loading", "empty"):
            return

        self.post_message(self.TaskSelected(task_id))

    def action_delete_task(self) -> None:
        """Request deletion of the currently selected task."""
        task_id = self.get_selected_task_id()

        if task_id is None:
            return

        self.post_message(self.TaskDeleteRequested(task_id))

    async def action_cycle_filter(self) -> None:
        """Cycle through task status filters."""
        filter_values = [opt[1] for opt in STATUS_FILTER_OPTIONS]
        current_index = (
            filter_values.index(self._status_filter) if self._status_filter in filter_values else 0
        )

        next_index = (current_index + 1) % len(filter_values)
        new_filter = filter_values[next_index]
        new_label = STATUS_FILTER_OPTIONS[next_index][0]

        self._status_filter = new_filter
        self._config_service.set_status_filter(new_filter)

        await self._apply_filters()

        if self.row_count > 0:
            self.move_cursor(row=0)

        self.post_message(self.TaskFilterChanged(new_filter, new_label))
        self.notify(f"Filter: {new_label}", severity="information")

    async def action_toggle_actionable_filter(self) -> None:
        """Toggle the actionable-only filter on/off."""
        self._show_actionable_only = not self._show_actionable_only

        await self._apply_filters()

        if self._show_actionable_only:
            filter_label = "Actionable"
            self.notify(
                "Filter: Actionable (pending tasks ready to work on)",
                severity="information",
            )
        else:
            filter_label = "All"
            self.notify("Filter: Actionable filter OFF", severity="information")

        filter_value = "actionable" if self._show_actionable_only else "all"
        self.post_message(self.TaskFilterChanged(filter_value, filter_label))

    async def action_open_search(self) -> None:
        """Open the search input for filtering tasks."""
        if self._search_active:
            return

        self._search_active = True

        search_input = Input(
            placeholder="Search tasks...",
            id="task-search-input",
            classes="task-search-input",
        )
        await self.mount(search_input, before=0)
        search_input.focus()

    async def _close_search(self, clear_filter: bool = False) -> None:
        """Close the search input and optionally clear the filter."""
        if not self._search_active:
            return

        self._search_active = False

        try:
            search_input = self.query_one("#task-search-input", Input)
            await search_input.remove()
        except Exception:
            pass

        if clear_filter:
            self._search_query = ""
            await self._apply_filters()

        self.focus()

    @on(Input.Changed, "#task-search-input")
    async def on_search_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes for real-time filtering."""
        self._search_query = event.value
        await self._apply_filters()

    @on(Input.Submitted, "#task-search-input")
    async def on_search_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input."""
        await self._close_search(clear_filter=False)

    async def on_key(self, event) -> None:
        """Handle key events for search escape and selection mode exit."""
        if getattr(self, "_search_active", False) and event.key == "escape":
            event.stop()
            await self._close_search(clear_filter=True)
        elif getattr(self, "_selection_mode", False) and event.key == "escape":
            event.stop()
            await self.action_toggle_selection_mode()

    async def action_toggle_selection_mode(self) -> None:
        """Toggle selection mode on/off."""
        self._selection_mode = not self._selection_mode

        if not self._selection_mode:
            self._selected_keys.clear()

        if self._selection_mode:
            self.border_title = "-- SELECTION MODE --"
            self.notify(
                "Selection mode ON - Use Space to select tasks",
                severity="information",
            )
        else:
            self.border_title = None
            self.notify("Selection mode OFF", severity="information")

        await self._refresh_current_display()

    async def _refresh_current_display(self) -> None:
        """Refresh the current display without re-fetching data."""
        await self._refresh_display(self._filtered_tasks)

    async def action_toggle_selection(self) -> None:
        """Toggle selection of the current row."""
        if not self._selection_mode:
            return

        task_id = self.get_selected_task_id()
        if task_id is None:
            return

        if task_id in self._selected_keys:
            self._selected_keys.remove(task_id)
        else:
            self._selected_keys.add(task_id)

        await self._refresh_display(self._filtered_tasks)

    async def action_select_all_visible(self) -> None:
        """Select all visible (filtered) rows, or deselect all if all are selected."""
        if not self._selection_mode:
            return

        visible_task_ids: set[str] = set()
        for task in self._filtered_tasks:
            task_id = task.get("id")
            if task_id and task_id not in ("loading", "empty"):
                visible_task_ids.add(task_id)

        if not visible_task_ids:
            return

        if visible_task_ids.issubset(self._selected_keys):
            self._selected_keys -= visible_task_ids
            self.notify(
                f"Deselected all {len(visible_task_ids)} visible tasks",
                severity="information",
            )
        else:
            self._selected_keys.update(visible_task_ids)
            self.notify(
                f"Selected all {len(visible_task_ids)} visible tasks",
                severity="information",
            )

        await self._refresh_display(self._filtered_tasks)

    async def action_open_bulk_actions(self) -> None:
        """Open bulk actions modal for selected tasks."""
        if not self._selected_keys:
            self.notify(
                "No tasks selected - use 'v' to enter selection mode",
                severity="warning",
            )
            return

        from task_crusade_mcp.tui.widgets.bulk_actions_modal import BulkActionsModal

        selected_tasks = [task for task in self._all_tasks if task.get("id") in self._selected_keys]

        modal = BulkActionsModal(
            selected_task_ids=list(self._selected_keys),
            selected_tasks=selected_tasks,
        )
        await self.app.push_screen(modal, callback=self._handle_bulk_action_result)

    def _handle_bulk_action_result(
        self, result: tuple[bool, str | None, dict[str, Any] | None] | bool | None
    ) -> None:
        """Handle bulk action modal result callback."""
        if not isinstance(result, tuple):
            return

        confirmed, action_type, action_params = result
        if not confirmed or not action_type or not action_params:
            return

        self.app.call_later(self._perform_bulk_action, action_type, action_params)

    async def _perform_bulk_action(self, action_type: str, action_params: dict[str, Any]) -> None:
        """Perform the actual bulk action asynchronously."""
        try:
            task_ids = list(self._selected_keys)

            if action_type == "delete":
                await self.data_service.bulk_delete_tasks(task_ids)
                self.notify(
                    f"Deleted {len(task_ids)} task{'s' if len(task_ids) != 1 else ''}",
                    severity="information",
                )

            elif action_type == "status":
                new_status = action_params.get("status")
                if new_status:
                    await self.data_service.bulk_update_task_status(task_ids, new_status)
                    self.notify(
                        f"Updated status for {len(task_ids)} task{'s' if len(task_ids) != 1 else ''}",
                        severity="information",
                    )

            elif action_type == "priority":
                new_priority = action_params.get("priority")
                if new_priority:
                    await self.data_service.bulk_update_task_priority(task_ids, new_priority)
                    self.notify(
                        f"Updated priority for {len(task_ids)} task{'s' if len(task_ids) != 1 else ''}",
                        severity="information",
                    )

            self._selected_keys.clear()
            self._selection_mode = False

            await self.refresh_tasks()

        except Exception as e:
            logger.exception(f"Bulk operation failed: {e}")
            self.notify(f"Bulk operation failed: {e}", severity="error")
