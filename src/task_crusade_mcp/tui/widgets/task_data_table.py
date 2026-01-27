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
    PRIORITY_CYCLE,
    PRIORITY_ICONS,
    RICH_STATUS_COLORS,
    STATUS_CYCLE,
    STATUS_FILTER_OPTIONS,
    STATUS_ICONS,
)
from task_crusade_mcp.tui.exceptions import DataFetchError, DataUpdateError
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

    class TaskDeleted(Message):
        """Message emitted when a task is deleted.

        Attributes:
            task_id: UUID of the deleted task.
        """

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    class TaskSearchChanged(Message):
        """Message emitted when the task search filter changes.

        Attributes:
            query: The current search query string.
            is_active: Whether search filter is currently active.
        """

        def __init__(self, query: str, is_active: bool) -> None:
            super().__init__()
            self.query = query
            self.is_active = is_active

    class TaskFilterChanged(Message):
        """Message emitted when the task status filter changes."""

        def __init__(self, filter_value: str, filter_label: str) -> None:
            super().__init__()
            self.filter_value = filter_value
            self.filter_label = filter_label

    class TaskStatusChanged(Message):
        """Message emitted when a task's status is changed.

        Attributes:
            task_id: UUID of the task.
            new_status: The new status value.
        """

        def __init__(self, task_id: str, new_status: str) -> None:
            super().__init__()
            self.task_id = task_id
            self.new_status = new_status

    class TaskPriorityChanged(Message):
        """Message emitted when a task's priority is changed.

        Attributes:
            task_id: UUID of the task.
            new_priority: The new priority value.
        """

        def __init__(self, task_id: str, new_priority: str) -> None:
            super().__init__()
            self.task_id = task_id
            self.new_priority = new_priority

    class TaskCreated(Message):
        """Message emitted when a new task is created.

        Attributes:
            task_id: UUID of the new task.
            task_data: Dictionary containing the new task's data.
        """

        def __init__(self, task_id: str, task_data: dict[str, Any]) -> None:
            super().__init__()
            self.task_id = task_id
            self.task_data = task_data

    class NewTaskRequested(Message):
        """Message emitted when user requests to create a new task.

        Attributes:
            campaign_id: UUID of the campaign to create the task in.
        """

        def __init__(self, campaign_id: str) -> None:
            super().__init__()
            self.campaign_id = campaign_id

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("g", "scroll_top", "First"),
        ("G", "scroll_bottom", "Last"),
        ("f", "cycle_filter", "Filter"),
        ("ctrl+a", "toggle_actionable_filter", "Actionable"),
        ("d", "delete_task", "Delete"),
        ("slash", "open_search", "Search"),
        ("ctrl+l", "clear_search", "Clear Search"),
        ("v", "toggle_selection_mode", "Selection Mode"),
        ("space", "toggle_selection", "Toggle Selection"),
        ("shift+a", "select_all_visible", "Select All"),
        ("b", "open_bulk_actions", "Bulk Actions"),
        # Quick status actions
        ("s", "cycle_status", "Cycle Status"),
        ("1", "set_status_pending", "Pending"),
        ("2", "set_status_in_progress", "In Progress"),
        ("3", "set_status_done", "Done"),
        ("4", "set_status_blocked", "Blocked"),
        # Quick priority actions
        ("p", "cycle_priority", "Cycle Priority"),
        ("exclamation_mark", "set_priority_critical", "Critical"),
        ("at", "set_priority_high", "High"),
        ("hash", "set_priority_medium", "Medium"),
        ("dollar_sign", "set_priority_low", "Low"),
        # Copy shortcuts
        ("y", "copy_task_id", "Copy ID"),
        ("Y", "copy_task_details", "Copy Details"),
        # Create new task
        ("n", "new_task", "New Task"),
        # Sorting
        ("S", "cycle_sort", "Sort"),
        # Dependencies
        ("D", "show_dependencies", "Dependencies"),
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

        # Sort state
        self._sort_mode: int = 0  # Index into SORT_MODES
        self._sort_modes: list[tuple[str, str]] = [
            ("priority", "Priority"),
            ("status", "Status"),
            ("created", "Created"),
            ("title", "Title"),
        ]

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

        # Clear selection state when loading new tasks (M2 fix)
        self._selected_keys.clear()

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
                task_cell = self._render_task_cell(task)
                priority_cell = self._render_priority_cell(task)

                self.add_row(task_cell, priority_cell, key=task_id)
        finally:
            self._is_loading = False

    async def _show_loading(self) -> None:
        """Display loading indicator."""
        self._is_loading = True
        self.clear()
        loading_row = ("Loading tasks...", "")
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

        empty_row = (message, "")
        self.add_row(*empty_row, key="empty")

    def _enrich_dependency_details(self) -> None:
        """Enrich tasks with dependency details for display.

        Adds two lists to each task:
        - dependency_details: Tasks that this task depends on (blocked by)
        - blocking_details: Tasks that depend on this task (blocking)
        """
        task_map = {task["id"]: task for task in self._all_tasks}

        # Build reverse dependency map (task_id -> list of tasks that depend on it)
        blocking_map: dict[str, list[dict[str, Any]]] = {
            task["id"]: [] for task in self._all_tasks
        }

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
                                "title": dep_task.get("title", "Unknown"),
                                "priority_order": dep_task.get("priority_order", "?"),
                                "status": dep_task.get("status", "unknown"),
                            }
                        )
                        # Add to reverse map
                        if dep_id in blocking_map:
                            blocking_map[dep_id].append(
                                {
                                    "id": task["id"],
                                    "title": task.get("title", "Unknown"),
                                    "priority_order": task.get("priority_order", "?"),
                                    "status": task.get("status", "unknown"),
                                }
                            )
                    else:
                        dep_details.append(
                            {
                                "id": dep_id,
                                "title": "Unknown",
                                "priority_order": "?",
                                "status": "unknown",
                            }
                        )
                task["dependency_details"] = dep_details

        # Add blocking details to each task
        for task in self._all_tasks:
            task["blocking_details"] = blocking_map.get(task["id"], [])

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
        filtered = self._apply_sort(filtered)

        self._filtered_tasks = filtered
        await self._refresh_display(filtered)

    def _apply_sort(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply current sort mode to tasks."""
        if not tasks:
            return tasks

        sort_key, _ = self._sort_modes[self._sort_mode]

        if sort_key == "priority":
            # Sort by priority order: critical > high > medium > low
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            return sorted(
                tasks,
                key=lambda t: priority_order.get(t.get("priority", "medium"), 2),
            )
        elif sort_key == "status":
            # Sort by status order: pending > in-progress > blocked > done
            status_order = {
                "pending": 0,
                "in-progress": 1,
                "blocked": 2,
                "done": 3,
                "cancelled": 4,
            }
            return sorted(
                tasks,
                key=lambda t: status_order.get(t.get("status", "pending"), 0),
            )
        elif sort_key == "created":
            # Sort by creation date, newest first
            return sorted(
                tasks,
                key=lambda t: t.get("created_at", ""),
                reverse=True,
            )
        elif sort_key == "title":
            # Sort alphabetically by title
            return sorted(
                tasks,
                key=lambda t: t.get("title", "").lower(),
            )

        return tasks

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
            task_cell = self._render_task_cell(task)
            priority_cell = self._render_priority_cell(task)

            self.add_row(task_cell, priority_cell, key=task_id)

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

    def get_selected_task(self) -> Optional[dict[str, Any]]:
        """Get the task data for the currently selected row."""
        task_id = self.get_selected_task_id()
        if task_id is None:
            return None

        return next((t for t in self._all_tasks if t.get("id") == task_id), None)

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
        self.notify(f"Filter: {new_label}", severity="information", timeout=1.5)

    async def action_toggle_actionable_filter(self) -> None:
        """Toggle the actionable-only filter on/off."""
        self._show_actionable_only = not self._show_actionable_only

        await self._apply_filters()

        if self._show_actionable_only:
            filter_label = "Actionable"
            self.notify(
                "Filter: Actionable (pending tasks ready to work on)",
                severity="information",
                timeout=1.5,
            )
        else:
            filter_label = "All"
            self.notify("Filter: Actionable filter OFF", severity="information", timeout=1.5)

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
        self.post_message(self.TaskSearchChanged(self._search_query, bool(self._search_query)))

    @on(Input.Submitted, "#task-search-input")
    async def on_search_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input."""
        await self._close_search(clear_filter=False)

    async def on_key(self, event) -> None:
        """Handle key events for search escape and selection mode exit."""
        if getattr(self, "_search_active", False) and event.key == "escape":
            event.stop()
            # Escape closes the search input but keeps the filter active
            await self._close_search(clear_filter=False)
        elif getattr(self, "_selection_mode", False) and event.key == "escape":
            event.stop()
            await self.action_toggle_selection_mode()

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
        await self._apply_filters()
        self.post_message(self.TaskSearchChanged("", False))
        self.notify("Search cleared", severity="information", timeout=1.5)

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

    # =========================================================================
    # Quick Status Actions (Phase 1.1)
    # =========================================================================

    async def action_cycle_status(self) -> None:
        """Cycle the status of the currently selected task."""
        task = self.get_selected_task()
        if task is None:
            return

        task_id = task.get("id")
        current_status = task.get("status", "pending")
        next_status = STATUS_CYCLE.get(current_status, "pending")

        await self._update_task_status(task_id, next_status)

    async def action_set_status_pending(self) -> None:
        """Set the selected task status to pending."""
        await self._set_task_status("pending")

    async def action_set_status_in_progress(self) -> None:
        """Set the selected task status to in-progress."""
        await self._set_task_status("in-progress")

    async def action_set_status_done(self) -> None:
        """Set the selected task status to done."""
        await self._set_task_status("done")

    async def action_set_status_blocked(self) -> None:
        """Set the selected task status to blocked."""
        await self._set_task_status("blocked")

    async def _set_task_status(self, status: str) -> None:
        """Set the selected task to a specific status."""
        task_id = self.get_selected_task_id()
        if task_id is None:
            return

        await self._update_task_status(task_id, status)

    async def _update_task_status(self, task_id: str, new_status: str) -> None:
        """Update task status and refresh display."""
        try:
            await self.data_service.update_task_status(task_id, new_status)

            # Update local task data for immediate UI feedback
            for task in self._all_tasks:
                if task.get("id") == task_id:
                    task["status"] = new_status
                    break

            # Refresh display without full reload
            await self._apply_filters()

            # Restore cursor position
            self._restore_cursor_to_task(task_id)

            self.notify(f"Status: {new_status}", severity="information", timeout=1.5)
            self.post_message(self.TaskStatusChanged(task_id, new_status))

        except DataUpdateError as e:
            logger.error(f"Failed to update task status: {e}")
            self.notify(f"Status update failed: {e}", severity="error")

    def _restore_cursor_to_task(self, task_id: str) -> None:
        """Restore cursor to a specific task after refresh."""
        try:
            for row_index, row in enumerate(self.ordered_rows):
                if row.key.value == task_id:
                    self.move_cursor(row=row_index)
                    return
        except (IndexError, AttributeError):
            pass

    # =========================================================================
    # Quick Priority Actions (Phase 1.2)
    # =========================================================================

    async def action_cycle_priority(self) -> None:
        """Cycle the priority of the currently selected task."""
        task = self.get_selected_task()
        if task is None:
            return

        task_id = task.get("id")
        current_priority = task.get("priority", "medium")
        next_priority = PRIORITY_CYCLE.get(current_priority, "medium")

        await self._update_task_priority(task_id, next_priority)

    async def action_set_priority_critical(self) -> None:
        """Set the selected task priority to critical."""
        await self._set_task_priority("critical")

    async def action_set_priority_high(self) -> None:
        """Set the selected task priority to high."""
        await self._set_task_priority("high")

    async def action_set_priority_medium(self) -> None:
        """Set the selected task priority to medium."""
        await self._set_task_priority("medium")

    async def action_set_priority_low(self) -> None:
        """Set the selected task priority to low."""
        await self._set_task_priority("low")

    async def _set_task_priority(self, priority: str) -> None:
        """Set the selected task to a specific priority."""
        task_id = self.get_selected_task_id()
        if task_id is None:
            return

        await self._update_task_priority(task_id, priority)

    async def _update_task_priority(self, task_id: str, new_priority: str) -> None:
        """Update task priority and refresh display."""
        try:
            await self.data_service.update_task_priority(task_id, new_priority)

            # Update local task data for immediate UI feedback
            for task in self._all_tasks:
                if task.get("id") == task_id:
                    task["priority"] = new_priority
                    break

            # Refresh display without full reload
            await self._apply_filters()

            # Restore cursor position
            self._restore_cursor_to_task(task_id)

            self.notify(f"Priority: {new_priority}", severity="information", timeout=1.5)
            self.post_message(self.TaskPriorityChanged(task_id, new_priority))

        except DataUpdateError as e:
            logger.error(f"Failed to update task priority: {e}")
            self.notify(f"Priority update failed: {e}", severity="error")

    # =========================================================================
    # Copy Shortcuts (Phase 1.3)
    # =========================================================================

    def action_copy_task_id(self) -> None:
        """Copy the selected task's ID to clipboard."""
        task_id = self.get_selected_task_id()
        if task_id is None:
            return

        self.app.copy_to_clipboard(task_id)
        self.notify("Task ID copied", severity="information", timeout=1.5)

    def action_copy_task_details(self) -> None:
        """Copy the selected task's full details to clipboard."""
        task = self.get_selected_task()
        if task is None:
            return

        # Format task details
        details_lines = [
            f"Title: {task.get('title', 'Unknown')}",
            f"ID: {task.get('id', 'Unknown')}",
            f"Status: {task.get('status', 'Unknown')}",
            f"Priority: {task.get('priority', 'Unknown')}",
        ]

        description = task.get("description", "")
        if description:
            details_lines.append(f"Description: {description}")

        details = "\n".join(details_lines)
        self.app.copy_to_clipboard(details)
        self.notify("Task details copied", severity="information", timeout=1.5)

    # =========================================================================
    # Sorting (Phase 4.1)
    # =========================================================================

    async def action_cycle_sort(self) -> None:
        """Cycle through sort modes."""
        self._sort_mode = (self._sort_mode + 1) % len(self._sort_modes)
        sort_key, sort_label = self._sort_modes[self._sort_mode]

        await self._apply_filters()

        self.notify(f"Sort: {sort_label}", severity="information", timeout=1.5)

    # =========================================================================
    # New Task Creation (Phase 3.1)
    # =========================================================================

    def action_new_task(self) -> None:
        """Request creation of a new task in the current campaign."""
        if self._campaign_id is None:
            self.notify("Select a campaign first", severity="warning")
            return

        self.post_message(self.NewTaskRequested(self._campaign_id))

    # =========================================================================
    # Dependency Visualization (Phase 7.1)
    # =========================================================================

    async def action_show_dependencies(self) -> None:
        """Show dependency modal for the selected task."""
        task = self.get_selected_task()
        if task is None:
            return

        task_id = task.get("id")
        task_title = task.get("title", "Unknown")

        # Get dependency details
        blocked_by = task.get("dependency_details", [])
        blocking = task.get("blocking_details", [])

        from task_crusade_mcp.tui.widgets.dependency_modal import DependencyModal

        modal = DependencyModal(
            task_id=task_id,
            task_title=task_title,
            blocked_by=blocked_by,
            blocking=blocking,
        )
        await self.app.push_screen(modal)
