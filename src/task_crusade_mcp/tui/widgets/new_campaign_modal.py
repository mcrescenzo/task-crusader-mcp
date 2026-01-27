"""New campaign creation modal widget for the TUI.

This module provides the NewCampaignModal that displays a form for creating
new campaigns.

Example usage:
    modal = NewCampaignModal()
    await self.app.push_screen(modal, callback=self._handle_new_campaign_result)
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea


class NewCampaignModal(ModalScreen):
    """Modal dialog for creating a new campaign."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    NewCampaignModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    NewCampaignModal > Container {
        width: 60;
        height: auto;
        min-height: 18;
        max-height: 30;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .new-campaign-title {
        text-style: bold;
        color: $primary;
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
        height: 4;
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

    class CampaignCreated(Message):
        """Emitted when a new campaign is created.

        Attributes:
            campaign_id: UUID of the newly created campaign.
            campaign_data: Dictionary containing the new campaign's data.
        """

        def __init__(self, campaign_id: str, campaign_data: dict) -> None:
            self.campaign_id = campaign_id
            self.campaign_data = campaign_data
            super().__init__()

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the new campaign modal.

        Args:
            name: Optional widget name.
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._error_message: str = ""

    def compose(self) -> ComposeResult:
        """Compose the modal layout with form fields."""
        priority_options = [
            ("Low", "low"),
            ("Medium", "medium"),
            ("High", "high"),
        ]

        with Container():
            yield Static("New Campaign", classes="new-campaign-title")

            with Vertical(classes="form-row"):
                yield Label("Name *", classes="form-label")
                yield Input(
                    placeholder="Enter campaign name...",
                    id="campaign-name-input",
                    classes="form-input",
                )

            with Vertical(classes="form-row"):
                yield Label("Priority", classes="form-label")
                yield Select(
                    priority_options,
                    value="medium",
                    id="campaign-priority-select",
                    classes="form-select",
                )

            with Vertical(classes="form-row"):
                yield Label("Description (optional)", classes="form-label")
                yield TextArea(
                    id="campaign-description-input",
                    classes="form-textarea",
                )

            yield Static("", id="error-display", classes="error-message")

            with Horizontal(classes="modal-buttons"):
                yield Button("Create", id="create-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="default")

    def on_mount(self) -> None:
        """Focus the name input on mount."""
        self.query_one("#campaign-name-input", Input).focus()

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
        if event.input.id == "campaign-name-input":
            self._validate_and_create()

    def _validate_and_create(self) -> None:
        """Validate form and create campaign if valid."""
        name_input = self.query_one("#campaign-name-input", Input)
        name = name_input.value.strip()

        if not name:
            self._show_error("Name is required")
            name_input.focus()
            return

        priority_select = self.query_one("#campaign-priority-select", Select)
        priority = str(priority_select.value) if priority_select.value else "medium"

        description_input = self.query_one("#campaign-description-input", TextArea)
        description = description_input.text.strip()

        # Return the form data for the parent to handle creation
        campaign_data = {
            "name": name,
            "priority": priority,
            "description": description,
        }

        self.dismiss((True, campaign_data))

    def _show_error(self, message: str) -> None:
        """Display an error message."""
        error_display = self.query_one("#error-display", Static)
        error_display.update(message)
