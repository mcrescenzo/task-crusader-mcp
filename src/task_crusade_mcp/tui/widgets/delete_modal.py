"""Delete confirmation modal widget for the TUI.

This module provides the DeleteModal that displays a confirmation dialog
before deleting tasks or campaigns.

Example usage:
    modal = DeleteModal(
        item_type="task",
        item_id="abc-123",
        item_name="JWT handler",
        counts={"research_items": 2, "acceptance_criteria": 5, "implementation_notes": 2}
    )
    await self.app.push_screen(modal)
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class DeleteModal(ModalScreen):
    """Modal dialog for confirming delete operations.

    Attributes:
        item_type: Type of item being deleted ("task" or "campaign").
        item_id: UUID of the item being deleted.
        item_name: Display name of the item being deleted.
        counts: Dictionary of associated data counts to display.
    """

    BINDINGS = [
        ("y", "confirm", "Yes, Delete"),
        ("n", "cancel", "Cancel"),
        ("escape", "cancel", "Cancel"),
    ]

    class DeleteConfirmed(Message):
        """Emitted when user confirms deletion."""

        def __init__(self, item_type: str, item_id: str) -> None:
            self.item_type = item_type
            self.item_id = item_id
            super().__init__()

    class DeleteCancelled(Message):
        """Emitted when user cancels deletion."""

    def __init__(
        self,
        item_type: str,
        item_id: str,
        item_name: str,
        counts: dict[str, int],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the delete confirmation modal.

        Args:
            item_type: Type of item being deleted ("task" or "campaign").
            item_id: UUID of the item being deleted.
            item_name: Display name of the item being deleted.
            counts: Dictionary of associated data counts.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._item_type = item_type
        self._item_id = item_id
        self._item_name = item_name
        self._counts = counts

    @property
    def item_type(self) -> str:
        """Get the type of item being deleted."""
        return self._item_type

    @property
    def item_id(self) -> str:
        """Get the ID of the item being deleted."""
        return self._item_id

    @property
    def item_name(self) -> str:
        """Get the name of the item being deleted."""
        return self._item_name

    @property
    def counts(self) -> dict[str, int]:
        """Get the counts of associated data."""
        return self._counts

    def compose(self) -> ComposeResult:
        """Compose the modal layout with warning, item info, and buttons."""
        title_text = f"⚠ DELETE {self._item_type.upper()}?"

        with Container():
            yield Static(title_text, classes="modal-title")

            yield Static("Are you sure you want to delete:", classes="modal-prompt")

            yield Static(f'"{self._item_name}"', classes="modal-item-name")

            if self._counts and any(v > 0 for v in self._counts.values()):
                with Vertical(classes="modal-warning-section"):
                    yield Static("This will also delete:", classes="modal-warning-header")

                    for key, count in self._counts.items():
                        if count > 0:
                            display_key = key.replace("_", " ")
                            yield Static(
                                f"• {count} {display_key}",
                                classes="modal-warning-item",
                            )

            yield Static(
                "This action cannot be undone.",
                classes="modal-undone-warning",
            )

            with Horizontal(classes="modal-buttons"):
                yield Button("[Y] Yes, Delete", id="confirm-button", variant="error")
                yield Button("[N] Cancel", id="cancel-button", variant="default")

    def action_confirm(self) -> None:
        """Handle confirmation action (Y key or confirm button)."""
        self.dismiss((True, self._item_type, self._item_id))

    def action_cancel(self) -> None:
        """Handle cancellation action (N key, Escape, or cancel button)."""
        self.dismiss((False, None, None))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm-button":
            self.action_confirm()
        elif event.button.id == "cancel-button":
            self.action_cancel()
