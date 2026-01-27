"""Dependency visualization modal widget for the TUI.

This module provides the DependencyModal that displays a task's dependency
tree, showing both blocking and blocked-by tasks.

Example usage:
    modal = DependencyModal(
        task_id="abc-123",
        task_title="Fix login bug",
        blocked_by=[...],
        blocking=[...],
    )
    await self.app.push_screen(modal)
"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static

from task_crusade_mcp.tui.constants import STATUS_ICONS


class DependencyModal(ModalScreen):
    """Modal dialog displaying task dependencies.

    Shows:
    - Tasks that block this task (must complete first)
    - Tasks that this task blocks (waiting on this task)
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    CSS = """
    DependencyModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    DependencyModal > Container {
        width: 65;
        height: auto;
        min-height: 15;
        max-height: 35;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .dep-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .dep-task-name {
        text-style: italic;
        color: $text;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .dep-scroll {
        width: 100%;
        height: auto;
        max-height: 24;
    }

    .dep-section-header {
        text-style: bold;
        color: $accent;
        width: 100%;
        padding: 1 0 0 0;
    }

    .dep-item {
        width: 100%;
        height: auto;
        padding: 0 0 0 2;
    }

    .dep-item-done {
        color: $success;
    }

    .dep-item-pending {
        color: $text-muted;
    }

    .dep-item-in-progress {
        color: $warning;
    }

    .dep-item-blocked {
        color: $error;
    }

    .dep-empty {
        color: $text-muted;
        text-style: italic;
        padding: 0 0 0 2;
    }

    .dep-footer {
        text-align: center;
        color: $text-muted;
        width: 100%;
        padding: 1 0 0 0;
    }
    """

    class DependencyTaskSelected(Message):
        """Emitted when user selects a dependency task to navigate to.

        Attributes:
            task_id: UUID of the selected task.
        """

        def __init__(self, task_id: str) -> None:
            self.task_id = task_id
            super().__init__()

    def __init__(
        self,
        task_id: str,
        task_title: str,
        blocked_by: list[dict[str, Any]],
        blocking: list[dict[str, Any]],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the dependency modal.

        Args:
            task_id: UUID of the task being viewed.
            task_title: Title of the task being viewed.
            blocked_by: List of tasks that must complete before this one.
            blocking: List of tasks that are waiting on this task.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._task_id = task_id
        self._task_title = task_title
        self._blocked_by = blocked_by
        self._blocking = blocking

    def compose(self) -> ComposeResult:
        """Compose the dependency modal layout."""
        with Container():
            yield Static("Dependencies", classes="dep-title")
            yield Static(f'"{self._task_title}"', classes="dep-task-name")

            with VerticalScroll(classes="dep-scroll"):
                # Blocked by section
                yield Static("BLOCKED BY (must complete first):", classes="dep-section-header")
                if self._blocked_by:
                    for dep in self._blocked_by:
                        yield self._render_dependency_item(dep)
                else:
                    yield Static("No dependencies", classes="dep-empty")

                # Blocking section
                yield Static("BLOCKING (waiting on this task):", classes="dep-section-header")
                if self._blocking:
                    for dep in self._blocking:
                        yield self._render_dependency_item(dep)
                else:
                    yield Static("No tasks waiting", classes="dep-empty")

            yield Static("Press Escape to close", classes="dep-footer")

    def _render_dependency_item(self, dep: dict[str, Any]) -> Static:
        """Render a single dependency item."""
        status = dep.get("status", "pending")
        title = dep.get("title", "Unknown")
        status_icon = STATUS_ICONS.get(status, "?")

        # Determine CSS class based on status
        status_class = f"dep-item-{status.replace('-', '-')}"

        # Format: icon [status] title
        text = f"{status_icon} [{status}] {title[:40]}"
        if len(title) > 40:
            text += "..."

        return Static(text, classes=f"dep-item {status_class}")

    def action_close(self) -> None:
        """Close the dependency modal."""
        self.dismiss()
