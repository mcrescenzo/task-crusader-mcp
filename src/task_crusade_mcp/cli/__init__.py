"""CLI interface for Task Crusade (optional [cli] extra)."""

import sys


def main() -> None:
    """Entry point for the crusader CLI."""
    try:
        from task_crusade_mcp.cli.app import create_app

        app = create_app()
        app()
    except ImportError as e:
        if "typer" in str(e).lower() or "rich" in str(e).lower():
            print("CLI requires typer and rich. Install with: pip install task-crusade-mcp[cli]")
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
