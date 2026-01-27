"""Help modal widget for the TUI.

This module provides the HelpModal that displays keyboard shortcuts
organized by category.

Example usage:
    modal = HelpModal()
    await self.app.push_screen(modal)
"""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

# Keyboard shortcuts organized by category
SHORTCUTS = {
    "Global": [
        ("q", "Quit application"),
        ("?", "Show this help"),
        ("Tab", "Next pane"),
        ("Shift+Tab", "Previous pane"),
        ("r", "Refresh all data"),
    ],
    "Campaign List": [
        ("j / k", "Navigate up/down"),
        ("g / G", "Jump to first/last"),
        ("f", "Cycle status filter"),
        ("/", "Open search"),
        ("Ctrl+L", "Clear search"),
        ("N", "New campaign"),
        ("d", "Delete campaign"),
        ("Enter", "Select campaign"),
    ],
    "Task List": [
        ("j / k", "Navigate up/down"),
        ("g / G", "Jump to first/last"),
        ("f", "Cycle status filter"),
        ("Ctrl+A", "Toggle actionable only"),
        ("/", "Open search"),
        ("Ctrl+L", "Clear search"),
        ("n", "New task"),
        ("d", "Delete task"),
        ("s", "Cycle status"),
        ("1/2/3/4", "Set status (pending/in-progress/done/blocked)"),
        ("p", "Cycle priority"),
        ("!/@ /#/$", "Set priority (critical/high/medium/low)"),
        ("y", "Copy task ID"),
        ("Y", "Copy task details"),
        ("v", "Toggle selection mode"),
        ("Space", "Toggle selection (in selection mode)"),
        ("Shift+A", "Select/deselect all visible"),
        ("b", "Bulk actions"),
    ],
    "Task Detail": [
        ("c", "Toggle criterion met/unmet"),
        ("j / k", "Navigate criteria"),
    ],
}


class HelpModal(ModalScreen):
    """Modal dialog displaying keyboard shortcuts."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("question_mark", "close", "Close"),
    ]

    CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    HelpModal > Container {
        width: 65;
        height: auto;
        min-height: 20;
        max-height: 40;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    .help-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .help-scroll {
        width: 100%;
        height: auto;
        max-height: 32;
    }

    .help-category {
        text-style: bold;
        color: $accent;
        width: 100%;
        padding: 1 0 0 0;
    }

    .help-shortcut {
        width: 100%;
        height: auto;
        padding: 0 0 0 2;
    }

    .shortcut-key {
        color: $warning;
        text-style: bold;
    }

    .shortcut-desc {
        color: $text;
    }

    .help-footer {
        text-align: center;
        color: $text-muted;
        width: 100%;
        padding: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the help modal layout."""
        with Container():
            yield Static("Keyboard Shortcuts", classes="help-title")

            with VerticalScroll(classes="help-scroll"):
                for category, shortcuts in SHORTCUTS.items():
                    yield Static(category, classes="help-category")

                    for key, description in shortcuts:
                        # Format the shortcut line
                        # markup=False prevents Rich from interpreting [] as markup tags
                        line = f"  [{key}]  {description}"
                        yield Static(line, classes="help-shortcut", markup=False)

            yield Static("Press any key to close", classes="help-footer")

    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss()

    def on_key(self, event) -> None:
        """Close on any key press."""
        self.dismiss()
