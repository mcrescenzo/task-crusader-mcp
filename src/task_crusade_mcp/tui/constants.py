"""TUI constants for consistent visual representation across all widgets.

This module provides status icons, colors, priority indicators, and status cycle
mappings used throughout the TUI interface for campaigns and tasks.
"""

# Status icons for task list display
STATUS_ICONS: dict[str, str] = {
    "done": "✓",
    "in-progress": "◐",
    "pending": "○",
    "cancelled": "✗",
    "blocked": "⊘",
}

# Status colors mapped to Textual CSS class names
STATUS_COLORS: dict[str, str] = {
    "done": "success",
    "in-progress": "warning",
    "pending": "muted",
    "cancelled": "error",
    "blocked": "error",
}

# Status colors for Rich Text styling (actual color names, not CSS classes)
# Use this when styling Rich Text objects with Text.append(style=...)
RICH_STATUS_COLORS: dict[str, str] = {
    "done": "green",
    "in-progress": "yellow",
    "pending": "dim",
    "cancelled": "red",
    "blocked": "red",
}

# Semantic colors for Rich Text styling (maps CSS semantic names to Rich colors)
# Use this when you need to style Rich Text with semantic colors like warning/success/error
# These correspond to the CSS class names in STATUS_COLORS but use actual Rich color names
RICH_SEMANTIC_COLORS: dict[str, str] = {
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "muted": "dim",
}

# Priority indicators using arrow symbols for DataTable rendering
# High priority: ↑ (upward arrow), Medium: → (rightward arrow), Low: ↓ (downward arrow)
PRIORITY_ICONS: dict[str, str] = {
    "high": "↑",
    "medium": "→",
    "low": "↓",
}

# Priority colors for Rich Text styling (used in DataTable rendering)
# Maps priority levels to Rich color names for colored text rendering
PRIORITY_COLORS: dict[str, str] = {
    "high": "red",
    "medium": "yellow",
    "low": "dim",
}

# Actionable task indicator (for pending tasks with all dependencies met)
ACTIONABLE_ICON: str = "▶"
ACTIONABLE_COLOR: str = "cyan"

# Status cycle for Space key toggle behavior
# Only includes the 3 main statuses - cancelled and blocked are not part of the toggle cycle
STATUS_CYCLE: dict[str, str] = {
    "pending": "in-progress",
    "in-progress": "done",
    "done": "pending",
}

# Status filter options for task list filtering
# Format: (display_label, value) - Textual Select widget format
STATUS_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("All", "all"),
    ("Actionable", "actionable"),
    ("Pending", "pending"),
    ("In Progress", "in-progress"),
    ("Done", "done"),
    ("Blocked", "blocked"),
    ("Cancelled", "cancelled"),
]

# Campaign status filter options
# "all" shows all campaigns (planning, active, paused, completed, cancelled)
# Order follows campaign lifecycle: planning → active → paused → completed → cancelled
CAMPAIGN_STATUS_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("All", "all"),
    ("Planning", "planning"),
    ("Active", "active"),
    ("Paused", "paused"),
    ("Completed", "completed"),
    ("Cancelled", "cancelled"),
]

# Campaign status colors for Rich Text styling (used in campaign list)
# Maps campaign status to Rich color names for colored campaign name rendering
CAMPAIGN_STATUS_COLORS: dict[str, str] = {
    "planning": "cyan",
    "active": "green",
    "paused": "yellow",
    "completed": "dim",
    "cancelled": "red",
}

# Campaign status icons for display
CAMPAIGN_STATUS_ICONS: dict[str, str] = {
    "planning": "◇",
    "active": "●",
    "paused": "◫",
    "completed": "✓",
    "cancelled": "✗",
}
