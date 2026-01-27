"""New task creation modal widget for the TUI.

This module provides the NewTaskModal that displays a form for creating
new tasks within a campaign.

Example usage:
    modal = NewTaskModal(campaign_id="abc-123", campaign_name="My Campaign")
    await self.app.push_screen(modal, callback=self._handle_new_task_result)
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea


class NewTaskModal(ModalScreen):
    """Modal dialog for creating a new task.

    Attributes:
        campaign_id: UUID of the campaign to create the task in.
        campaign_name: Display name of the campaign.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    NewTaskModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    NewTaskModal > Container {
        width: 60;
        height: auto;
        min-height: 20;
        max-height: 35;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .new-task-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .new-task-campaign {
        color: $text-muted;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .form-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    .form-label {
        width: 100%;
        height: 1;
        color: $text;
        padding: 0 0 0 0;
    }

    .form-input {
        width: 100%;
        height: 3;
    }

    .form-select {
        width: 100%;
        height: 3;
    }

    .form-textarea {
        width: 100%;
        height: 5;
    }

    .modal-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    .modal-buttons Button {
        margin: 0 1;
    }

    #create-button {
        background: $success;
    }

    #cancel-button {
        background: $surface-darken-1;
    }

    .error-message {
        color: $error;
        text-align: center;
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
    }
    """

    class TaskCreated(Message):
        """Emitted when a new task is created.

        Attributes:
            task_id: UUID of the newly created task.
            task_data: Dictionary containing the new task's data.
        """

        def __init__(self, task_id: str, task_data: dict) -> None:
            self.task_id = task_id
            self.task_data = task_data
            super().__init__()

    def __init__(
        self,
        campaign_id: str,
        campaign_name: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the new task modal.

        Args:
            campaign_id: UUID of the campaign to create the task in.
            campaign_name: Display name of the campaign.
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._campaign_id = campaign_id
        self._campaign_name = campaign_name
        self._error_message: str = ""

    @property
    def campaign_id(self) -> str:
        """Get the campaign ID."""
        return self._campaign_id

    @property
    def campaign_name(self) -> str:
        """Get the campaign name."""
        return self._campaign_name

    def compose(self) -> ComposeResult:
        """Compose the modal layout with form fields."""
        priority_options = [
            ("Low", "low"),
            ("Medium", "medium"),
            ("High", "high"),
            ("Critical", "critical"),
        ]

        with Container():
            yield Static("New Task", classes="new-task-title")
            yield Static(f"Campaign: {self._campaign_name}", classes="new-task-campaign")

            with Vertical(classes="form-row"):
                yield Label("Title *", classes="form-label")
                yield Input(
                    placeholder="Enter task title...",
                    id="task-title-input",
                    classes="form-input",
                )

            with Vertical(classes="form-row"):
                yield Label("Priority", classes="form-label")
                yield Select(
                    priority_options,
                    value="medium",
                    id="task-priority-select",
                    classes="form-select",
                )

            with Vertical(classes="form-row"):
                yield Label("Description (optional)", classes="form-label")
                yield TextArea(
                    id="task-description-input",
                    classes="form-textarea",
                )

            yield Static("", id="error-display", classes="error-message")

            with Horizontal(classes="modal-buttons"):
                yield Button("Create", id="create-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="default")

    def on_mount(self) -> None:
        """Focus the title input on mount."""
        self.query_one("#task-title-input", Input).focus()

    def action_cancel(self) -> None:
        """Handle cancellation action."""
        self.dismiss((False, None))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "create-button":
            self._validate_and_create()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "task-title-input":
            self._validate_and_create()

    def _validate_and_create(self) -> None:
        """Validate form and create task if valid."""
        title_input = self.query_one("#task-title-input", Input)
        title = title_input.value.strip()

        if not title:
            self._show_error("Title is required")
            title_input.focus()
            return

        priority_select = self.query_one("#task-priority-select", Select)
        priority = str(priority_select.value) if priority_select.value else "medium"

        description_input = self.query_one("#task-description-input", TextArea)
        description = description_input.text.strip()

        # Return the form data for the parent to handle creation
        task_data = {
            "campaign_id": self._campaign_id,
            "title": title,
            "priority": priority,
            "description": description,
        }

        self.dismiss((True, task_data))

    def _show_error(self, message: str) -> None:
        """Display an error message."""
        error_display = self.query_one("#error-display", Static)
        error_display.update(message)
