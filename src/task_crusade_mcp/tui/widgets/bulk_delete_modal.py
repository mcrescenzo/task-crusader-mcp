"""Bulk delete confirmation modal widget for the TUI.

This module provides the BulkDeleteModal that displays a confirmation dialog
before bulk deleting tasks.

Example usage:
    modal = BulkDeleteModal(
        selected_task_ids=["id1", "id2", "id3"],
        selected_tasks=[task1_data, task2_data, task3_data]
    )
    result = await self.app.push_screen(modal)
"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from task_crusade_mcp.tui.constants import STATUS_ICONS


class BulkDeleteModal(ModalScreen):
    """Modal dialog for confirming bulk delete operations.

    Attributes:
        selected_task_ids: List of task IDs to delete.
        selected_tasks: List of task data dictionaries for preview.
    """

    BINDINGS = [
        ("y", "confirm", "Yes, Delete"),
        ("n", "cancel", "Cancel"),
        ("escape", "cancel", "Cancel"),
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
        """Initialize the bulk delete confirmation modal.

        Args:
            selected_task_ids: List of task IDs to delete.
            selected_tasks: List of task data dictionaries for preview.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._selected_task_ids = selected_task_ids
        self._selected_tasks = selected_tasks

    @property
    def selected_task_ids(self) -> list[str]:
        """Get the list of selected task IDs."""
        return self._selected_task_ids

    @property
    def selected_tasks(self) -> list[dict[str, Any]]:
        """Get the list of selected task data."""
        return self._selected_tasks

    def compose(self) -> ComposeResult:
        """Compose the modal layout with warning, task preview, and buttons."""
        count = len(self._selected_task_ids)
        title_text = f"⚠ DELETE {count} TASK{'S' if count != 1 else ''}?"

        with Container():
            yield Static(title_text, classes="modal-title")

            yield Static(
                f"Are you sure you want to delete {count} task{'s' if count != 1 else ''}?",
                classes="modal-prompt",
            )

            with Vertical(classes="modal-warning-section"):
                yield Static("Tasks to be deleted:", classes="modal-warning-header")

                preview_tasks = self._selected_tasks[:5]
                for task in preview_tasks:
                    title = task.get("title", "Unnamed Task")
                    status = task.get("status", "pending")
                    status_icon = STATUS_ICONS.get(status, "○")
                    priority_order = task.get("priority_order", "?")

                    if len(title) > 35:
                        title = title[:32] + "..."

                    yield Static(
                        f"• {status_icon} #{priority_order} {title}",
                        classes="modal-warning-item",
                    )

                if count > 5:
                    yield Static(
                        f"• ... and {count - 5} more",
                        classes="modal-warning-item",
                    )

            yield Static(
                "This action cannot be undone.",
                classes="modal-undone-warning",
            )

            with Horizontal(classes="modal-buttons"):
                yield Button("[Y] Yes, Delete All", id="confirm-button", variant="error")
                yield Button("[N] Cancel", id="cancel-button", variant="default")

    def action_confirm(self) -> None:
        """Handle confirmation action (Y key or confirm button)."""
        self.dismiss((True, "delete", {}))

    def action_cancel(self) -> None:
        """Handle cancellation action (N key, Escape, or cancel button)."""
        self.dismiss((False, None, None))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm-button":
            self.action_confirm()
        elif event.button.id == "cancel-button":
            self.action_cancel()
