"""Task Crusade TUI Application.

This module provides the main TUI application that composes the 3-pane layout
(Campaign List | Task Table | Task Detail) with navigation and data services.

Example usage:
    from task_crusade_mcp.tui.app import CrusaderTUI

    app = CrusaderTUI()
    app.run()
"""

import sys
from pathlib import Path

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import Footer, Header
except ImportError:
    print("TUI requires textual. Install with: pip install task-crusader-mcp[tui]")
    sys.exit(1)

from task_crusade_mcp.tui.screens.main import CampaignTaskPane
from task_crusade_mcp.tui.services.config_service import TUIConfigService
from task_crusade_mcp.tui.services.data_service import TUIDataService


class CrusaderTUI(App):
    """Task Crusade TUI Application.

    A 3-pane terminal user interface for managing campaigns and tasks.

    Layout:
        ┌────────────────────────────────────────────────────────────────┐
        │ Header: Task Crusade                                           │
        ├─────────┬─────────────────────┬────────────────────────────────┤
        │ CAMPAIGNS│ TASKS              │ DETAIL                         │
        │   20%   │       40%          │           40%                  │
        └─────────┴─────────────────────┴────────────────────────────────┘
        │ Footer: Keybindings                                            │
        └────────────────────────────────────────────────────────────────┘

    Keyboard Navigation:
        Tab/Shift+Tab: Cycle between panes
        j/k: Navigate within lists (vim-style)
        Enter: Select item
        f: Cycle status filter
        /: Toggle search
        d: Delete selected item
        v: Toggle multi-select mode (tasks)
        b: Bulk actions (tasks)
        c: Toggle acceptance criteria (detail)
        r: Refresh data
        q: Quit application
    """

    TITLE = "Task Crusade"
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    # Disable the default command palette (not implemented)
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "help", "Help", show=False),
    ]

    def __init__(self) -> None:
        """Initialize the TUI application with data and config services."""
        super().__init__()
        self._data_service = TUIDataService()
        self._config_service = TUIConfigService()

    def compose(self) -> ComposeResult:
        """Compose the application layout with header, main pane, and footer."""
        yield Header()
        yield CampaignTaskPane(
            data_service=self._data_service,
            config_service=self._config_service,
        )
        yield Footer()

    async def action_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        from task_crusade_mcp.tui.widgets.help_modal import HelpModal

        await self.push_screen(HelpModal())
