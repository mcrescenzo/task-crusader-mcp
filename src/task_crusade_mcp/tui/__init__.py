"""TUI interface for Task Crusade (optional [tui] extra).

This package provides a full-featured terminal user interface for managing
campaigns and tasks using a 3-pane layout.

Layout:
    - Campaign List (20%): Browse and filter campaigns
    - Task Table (40%): View tasks with filtering, sorting, and bulk operations
    - Task Detail (40%): Full task details with acceptance criteria, notes, etc.

Example usage:
    from task_crusade_mcp.tui import main
    main()

Or from command line:
    crusader-tui
"""

import sys


def main() -> None:
    """Entry point for the crusader-tui command."""
    try:
        from textual.app import App  # noqa: F401
    except ImportError:
        print("TUI requires textual. Install with: pip install task-crusader-mcp[tui]")
        sys.exit(1)

    from task_crusade_mcp.tui.app import CrusaderTUI

    app = CrusaderTUI()
    app.run()


__all__ = ["main"]


if __name__ == "__main__":
    main()
