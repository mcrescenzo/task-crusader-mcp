"""Bulk actions modal widget for the TUI.

This module provides the BulkActionsModal that displays action options
for bulk operations on selected tasks.

Example usage:
    modal = BulkActionsModal(
        selected_task_ids=["id1", "id2", "id3"],
        selected_tasks=[task1_data, task2_data, task3_data]
    )
    result = await self.app.push_screen(modal)
"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from task_crusade_mcp.tui.constants import STATUS_ICONS


class BulkActionsModal(ModalScreen):
    """Modal dialog for selecting bulk actions on tasks.

    Attributes:
        selected_task_ids: List of task IDs to perform bulk action on.
        selected_tasks: List of task data dictionaries for preview.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("d", "select_delete", "Delete"),
        ("s", "select_status", "Status"),
        ("p", "select_priority", "Priority"),
    ]

    STATUS_OPTIONS = [
        ("Pending", "pending"),
        ("In Progress", "in-progress"),
        ("Done", "done"),
        ("Blocked", "blocked"),
        ("Cancelled", "cancelled"),
    ]

    PRIORITY_OPTIONS = [
        ("High", "high"),
        ("Medium", "medium"),
        ("Low", "low"),
    ]

    def __init__(
        self,
        selected_task_ids: list[str],
        selected_tasks: list[dict[str, Any]],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the bulk actions modal.

        Args:
            selected_task_ids: List of task IDs to perform bulk action on.
            selected_tasks: List of task data dictionaries for preview.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._selected_task_ids = selected_task_ids
        self._selected_tasks = selected_tasks
        self._selected_action: str | None = None
        self._action_params: dict[str, Any] = {}

    @property
    def selected_task_ids(self) -> list[str]:
        """Get the list of selected task IDs."""
        return self._selected_task_ids

    @property
    def selected_tasks(self) -> list[dict[str, Any]]:
        """Get the list of selected task data."""
        return self._selected_tasks

    def compose(self) -> ComposeResult:
        """Compose the modal layout with task preview and action buttons."""
        count = len(self._selected_task_ids)

        with Container(id="bulk-actions-modal-container"):
            yield Label(f"Bulk Actions ({count} tasks)", id="bulk-actions-modal-title")

            with Vertical(id="bulk-actions-preview"):
                yield Static("Selected tasks:", classes="preview-header")

                preview_tasks = self._selected_tasks[:5]
                for task in preview_tasks:
                    title = task.get("title", "Unnamed Task")
                    status = task.get("status", "pending")
                    status_icon = STATUS_ICONS.get(status, "○")
                    priority_order = task.get("priority_order", "?")

                    if len(title) > 40:
                        title = title[:37] + "..."

                    yield Static(
                        f"  {status_icon} #{priority_order} {title}",
                        classes="preview-task-item",
                    )

                if count > 5:
                    yield Static(
                        f"  ... and {count - 5} more",
                        classes="preview-more",
                    )

            with Vertical(id="bulk-actions-section"):
                yield Static("Select action:", classes="action-header")

                yield Button(
                    "[D] Delete All",
                    id="action-delete",
                    variant="error",
                    classes="action-button",
                )

                with Horizontal(classes="action-row"):
                    yield Label("[S] Change Status:", classes="action-label")
                    yield Select(
                        options=self.STATUS_OPTIONS,
                        id="status-select",
                        classes="action-select",
                    )

                with Horizontal(classes="action-row"):
                    yield Label("[P] Change Priority:", classes="action-label")
                    yield Select(
                        options=self.PRIORITY_OPTIONS,
                        id="priority-select",
                        classes="action-select",
                    )

            with Horizontal(id="bulk-actions-modal-buttons"):
                yield Button("Cancel", id="cancel-button", variant="default")

    def action_cancel(self) -> None:
        """Handle cancellation action (Escape or cancel button)."""
        self.dismiss((False, None, None))

    def action_select_delete(self) -> None:
        """Handle delete action shortcut (D key)."""
        self._handle_delete_action()

    def action_select_status(self) -> None:
        """Handle status action shortcut (S key) - focus status select."""
        try:
            status_select = self.query_one("#status-select", Select)
            status_select.focus()
        except Exception:
            pass

    def action_select_priority(self) -> None:
        """Handle priority action shortcut (P key) - focus priority select."""
        try:
            priority_select = self.query_one("#priority-select", Select)
            priority_select.focus()
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "action-delete":
            self._handle_delete_action()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def _handle_delete_action(self) -> None:
        """Handle delete action - show confirmation and dismiss."""
        from task_crusade_mcp.tui.widgets.bulk_delete_modal import BulkDeleteModal

        modal = BulkDeleteModal(
            selected_task_ids=self._selected_task_ids,
            selected_tasks=self._selected_tasks,
        )
        self.app.push_screen(modal, callback=self._handle_delete_confirmation)

    def _handle_delete_confirmation(
        self, result: tuple[bool, str | None, dict[str, Any] | None] | bool
    ) -> None:
        """Handle delete confirmation modal result."""
        if isinstance(result, tuple) and result[0]:
            self.dismiss(result)

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select dropdown changes."""
        if event.select.id == "status-select" and event.value != Select.BLANK:
            self.dismiss((True, "status", {"status": str(event.value)}))
        elif event.select.id == "priority-select" and event.value != Select.BLANK:
            self.dismiss((True, "priority", {"priority": str(event.value)}))
