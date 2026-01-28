"""Task detail widget for the TUI Task Detail pane.

This module provides the TaskDetailWidget that displays comprehensive task
information in a scrollable panel.

Example usage:
    task_detail = TaskDetailWidget()
    await task_detail.load_task(task_id)
"""

import logging
from typing import Any

from rich.text import Text
from textual import on
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.events import Click
from textual.message import Message
from textual.widgets import Button, LoadingIndicator, Static

from task_crusade_mcp.tui.constants import (
    PRIORITY_ICONS,
    RICH_STATUS_COLORS,
    STATUS_ICONS,
)
from task_crusade_mcp.tui.exceptions import DataFetchError, DataUpdateError
from task_crusade_mcp.tui.services.data_service import TUIDataService

logger = logging.getLogger(__name__)


class ClickableCriterion(Static):
    """A clickable acceptance criterion widget."""

    class CriterionClicked(Message):
        """Emitted when a criterion is clicked."""

        def __init__(self, criterion_index: int, entity_id: str) -> None:
            super().__init__()
            self.criterion_index = criterion_index
            self.entity_id = entity_id

    def __init__(
        self,
        content: Text,
        criterion_index: int,
        entity_id: str,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(content, id=id, classes=classes)
        self._criterion_index = criterion_index
        self._entity_id = entity_id

    def on_click(self, event: Click) -> None:
        """Handle click by emitting CriterionClicked message."""
        event.stop()
        self.post_message(self.CriterionClicked(self._criterion_index, self._entity_id))


class TaskDetailWidget(VerticalScroll):
    """Task detail widget displaying comprehensive task information.

    Attributes:
        data_service: TUIDataService instance for fetching task data.
        _task_id: ID of the currently displayed task.
        _is_loading: Boolean indicating if data is currently being loaded.
        _task_data: Dictionary containing the current task's data.
    """

    BINDINGS = [
        Binding("c", "toggle_criterion", "Toggle Criterion", show=True),
        Binding("j", "next_criterion", "Next Criterion", show=False),
        Binding("k", "prev_criterion", "Prev Criterion", show=False),
        Binding("down", "next_criterion", "Next Criterion", show=False),
        Binding("up", "prev_criterion", "Prev Criterion", show=False),
    ]

    def __init__(
        self,
        data_service: TUIDataService | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the task detail widget."""
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.data_service = data_service or TUIDataService()
        self._task_id: str | None = None
        self._is_loading = False
        self._task_data: dict[str, Any] | None = None
        self._selected_criterion_index: int = -1
        self._criteria_data: list[dict[str, Any]] = []
        self._criterion_widget_ids: list[str] = []
        self._campaign_id: str | None = None
        self._campaign_data: dict[str, Any] | None = None
        self._display_mode: str = "empty"
        self._load_generation: int = 0

    def compose(self):
        """Compose initial empty widget."""
        yield Static(
            "Select a campaign or task to view details",
            classes="empty-message",
        )

    async def load_task(self, task_id: str) -> None:
        """Load task details from the data service and display them."""
        self._load_generation += 1
        current_generation = self._load_generation

        self._task_id = task_id
        self._campaign_id = None
        self._campaign_data = None
        self._display_mode = "task"
        self._is_loading = True
        await self._show_loading()

        try:
            self._task_data = await self.data_service.get_task_detail(task_id=task_id)

            if current_generation != self._load_generation:
                return

            if self._task_data:
                await self._render_task_detail()
            else:
                await self._show_not_found()
        except DataFetchError as e:
            logger.error(f"Failed to load task {task_id}: {e}")

            if current_generation == self._load_generation:
                self.notify(str(e), severity="error")
                self._task_data = None
                await self._show_error(str(e))
        finally:
            self._is_loading = False

    async def clear_task(self) -> None:
        """Clear the task detail display."""
        self._task_id = None
        self._task_data = None
        self._campaign_id = None
        self._campaign_data = None
        self._display_mode = "empty"
        self._selected_criterion_index = -1
        self._criteria_data = []
        self._criterion_widget_ids = []
        await self._clear_content()
        await self.mount(
            Static(
                "Select a campaign or task to view details",
                classes="empty-message",
            )
        )

    async def load_campaign_summary(self, campaign_id: str) -> None:
        """Load campaign summary and display it in the detail pane."""
        self._load_generation += 1
        current_generation = self._load_generation

        self._campaign_id = campaign_id
        self._task_id = None
        self._task_data = None
        self._display_mode = "campaign"
        self._is_loading = True
        self._selected_criterion_index = -1
        self._criteria_data = []
        self._criterion_widget_ids = []
        await self._show_loading()

        try:
            self._campaign_data = await self.data_service.get_campaign_summary(campaign_id)

            if current_generation != self._load_generation:
                return

            if self._campaign_data:
                await self._render_campaign_summary()
            else:
                await self._show_not_found_campaign()
        except DataFetchError as e:
            logger.error(f"Failed to load campaign {campaign_id}: {e}")

            if current_generation == self._load_generation:
                self.notify(str(e), severity="error")
                self._campaign_data = None
                await self._show_error(str(e))
        finally:
            self._is_loading = False

    async def refresh_task(self) -> None:
        """Refresh the current task or campaign by reloading data."""
        if self._task_id:
            await self.load_task(task_id=self._task_id)
        elif self._campaign_id:
            await self.load_campaign_summary(campaign_id=self._campaign_id)

    async def _clear_content(self) -> None:
        """Clear all content from the widget."""
        await self.remove_children()

    async def _show_loading(self) -> None:
        """Display loading spinner while fetching data."""
        await self._clear_content()
        loading_container = Static(classes="loading-container")
        loading_container.compose_add_child(LoadingIndicator())
        await self.mount(loading_container)

    async def _show_not_found(self) -> None:
        """Display message when task is not found."""
        await self._clear_content()
        await self.mount(Static("Task not found", classes="empty-message"))

    async def _show_not_found_campaign(self) -> None:
        """Display message when campaign is not found."""
        await self._clear_content()
        await self.mount(Static("Campaign not found", classes="empty-message"))

    async def _show_error(self, message: str) -> None:
        """Display error message."""
        await self._clear_content()
        await self.mount(Static(f"Error loading task:\n{message}", classes="empty-message"))

    async def _render_task_detail(self) -> None:
        """Render the full task detail view."""
        await self._clear_content()

        if not self._task_data:
            return

        task = self._task_data

        title = task.get("title", "Unnamed Task")
        await self.mount(Static(title, classes="task-detail-title"))

        await self._render_metadata(task)
        await self._render_section("DESCRIPTION", task.get("description", ""))
        await self._render_dependencies(task)
        await self._render_acceptance_criteria(task)
        await self._render_research(task)
        await self._render_implementation_notes(task)
        await self._render_testing_steps(task)

    async def _render_metadata(self, task: dict[str, Any]) -> None:
        """Render task metadata."""
        status = task.get("status", "pending")
        priority = task.get("priority", "medium")
        task_type = task.get("type", "code")
        category = task.get("category", "")
        created_at = task.get("created_at", "")
        updated_at = task.get("updated_at", "")

        status_icon = STATUS_ICONS.get(status, STATUS_ICONS["pending"])
        status_color = RICH_STATUS_COLORS.get(status, "dim")
        priority_icon = PRIORITY_ICONS.get(priority, PRIORITY_ICONS["medium"])

        task_id = task.get("id", "")
        if task_id:
            id_row = Horizontal(classes="id-row")
            copy_button = Button("Copy", id="copy-task-id", classes="copy-id-button")
            id_text = Static(task_id, classes="id-text")
            id_row.compose_add_child(copy_button)
            id_row.compose_add_child(id_text)
            await self.mount(id_row)

        metadata_text = Text()

        metadata_text.append("Status: ")
        metadata_text.append(f"{status_icon} {status}", style=status_color)
        metadata_text.append("\n")

        metadata_text.append(f"Priority: {priority_icon} {priority}\n")
        metadata_text.append(f"Type: {task_type}\n")

        if category:
            metadata_text.append(f"Category: {category}\n")

        if created_at:
            date_str = str(created_at)[:10] if len(str(created_at)) >= 10 else created_at
            metadata_text.append(f"Created: {date_str}\n")

        if updated_at:
            date_str = str(updated_at)[:10] if len(str(updated_at)) >= 10 else updated_at
            metadata_text.append(f"Updated: {date_str}")

        await self.mount(Static(metadata_text, classes="task-detail-metadata"))

    async def _render_section(self, title: str, content: str, show_empty: bool = True) -> None:
        """Render a section with header and content."""
        if not content and not show_empty:
            return

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static(title, classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        display_content = content if content else "(No content)"
        await self.mount(Static(display_content, classes="task-detail-content"))

    async def _render_dependencies(self, task: dict[str, Any]) -> None:
        """Render dependencies section."""
        dependencies = task.get("dependencies", [])
        dependency_details = task.get("dependency_details", [])

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("DEPENDENCIES", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not dependencies:
            await self.mount(Static("(No dependencies)", classes="task-detail-content"))
            return

        await self.mount(Static("Upstream (blocks this task):", classes="task-detail-content"))

        for dep_id in dependencies:
            await self._render_dependency_item(dep_id, dependency_details)

    async def _render_dependency_item(
        self,
        dep_id: str,
        details_list: list[dict[str, Any]],
    ) -> None:
        """Render a single dependency item with status icon."""
        dep_detail = next(
            (d for d in details_list if d.get("id") == dep_id),
            None,
        )

        dep_text = Text()
        dep_text.append("  ")

        if dep_detail:
            dep_title = dep_detail.get("title", "Unknown")
            dep_status = dep_detail.get("status", "unknown")

            status_icon = STATUS_ICONS.get(dep_status, STATUS_ICONS["pending"])
            status_color = RICH_STATUS_COLORS.get(dep_status, "dim")

            dep_text.append(f"{status_icon} ", style=status_color)
            if dep_status == "done":
                dep_text.append(f"#{dep_id[:8]} {dep_title}", style="dim")
            else:
                dep_text.append(f"#{dep_id[:8]} {dep_title}")
        else:
            dep_text.append(f"○ #{dep_id[:8]}", style="dim")

        await self.mount(Static(dep_text, classes="task-detail-item"))

    async def _render_acceptance_criteria(self, task: dict[str, Any]) -> None:
        """Render acceptance criteria with met/unmet indicators."""
        criteria = task.get("acceptance_criteria_details", [])
        task_id_prefix = task.get("id", "unknown")[:8]

        self._criteria_data = list(criteria)
        self._criterion_widget_ids = []

        if criteria and self._selected_criterion_index < 0:
            self._selected_criterion_index = 0

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("ACCEPTANCE CRITERIA", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not criteria:
            await self.mount(Static("(No acceptance criteria)", classes="task-detail-content"))
            self._selected_criterion_index = -1
            return

        met_count = 0
        total_count = len(criteria)

        for idx, criterion in enumerate(criteria):
            criterion_text = (
                criterion.get("content") or criterion.get("notes") or criterion.get("name", "")
            )
            is_met = criterion.get("is_met", False)

            if is_met:
                met_count += 1

            crit_display = Text()
            if is_met:
                crit_display.append("[✓] ", style="green")
                crit_display.append(criterion_text)
            else:
                crit_display.append("[ ] ", style="dim")
                crit_display.append(criterion_text)

            is_selected = idx == self._selected_criterion_index
            css_classes = "criteria-item"
            if is_selected:
                css_classes += " criteria-selected"

            widget_id = f"criterion-{task_id_prefix}-{idx}"
            self._criterion_widget_ids.append(widget_id)
            entity_id = criterion.get("id", "")
            await self.mount(
                ClickableCriterion(
                    crit_display,
                    criterion_index=idx,
                    entity_id=entity_id,
                    id=widget_id,
                    classes=css_classes,
                )
            )

        progress_text = Text()
        progress_text.append(f"Progress: {met_count}/{total_count} criteria met")
        await self.mount(
            Static(
                progress_text,
                id=f"criteria-progress-{task_id_prefix}",
                classes="task-detail-content",
            )
        )

    async def _render_research(self, task: dict[str, Any]) -> None:
        """Render research items grouped by type."""
        research = task.get("research", [])

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("RESEARCH", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not research:
            await self.mount(Static("(No research items)", classes="task-detail-content"))
            return

        research_by_type: dict[str, list[dict[str, Any]]] = {}
        for item in research:
            item_type = item.get("type", "general")
            if item_type not in research_by_type:
                research_by_type[item_type] = []
            research_by_type[item_type].append(item)

        for research_type, items in research_by_type.items():
            type_header = Text()
            type_header.append(f"[{research_type}]", style="italic")
            await self.mount(Static(type_header, classes="task-detail-item-header"))

            for item in items:
                notes = item.get("content", "")
                if notes:
                    await self.mount(Static(notes, classes="task-detail-item", markup=False))

    async def _render_implementation_notes(self, task: dict[str, Any]) -> None:
        """Render implementation notes with type and timestamp."""
        notes = task.get("implementation_notes", [])

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("IMPLEMENTATION NOTES", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not notes:
            await self.mount(Static("(No implementation notes)", classes="task-detail-content"))
            return

        for note in notes:
            note_type = note.get("note_type", "general")
            created_at = note.get("created_at", "")
            content = note.get("content", "")

            date_str = ""
            if created_at:
                date_str = str(created_at)[:10] if len(str(created_at)) >= 10 else created_at

            header_text = Text()
            header_text.append(f"[{note_type}]", style="italic")
            if date_str:
                header_text.append(f" {date_str}", style="dim")
            await self.mount(Static(header_text, classes="task-detail-item-header"))

            if content:
                await self.mount(Static(content, classes="task-detail-item", markup=False))

    async def _render_testing_steps(self, task: dict[str, Any]) -> None:
        """Render testing strategy steps with status indicators."""
        steps = task.get("testing_steps", [])

        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("TESTING STRATEGY", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not steps:
            await self.mount(Static("(No testing steps)", classes="task-detail-content"))
            return

        step_status_icons = {
            "pending": "○",
            "passed": "✓",
            "failed": "✗",
            "skipped": "⊘",
        }

        step_type_styles = {
            "setup": "cyan",
            "trigger": "yellow",
            "verify": "green",
            "cleanup": "dim",
            "debug": "magenta",
            "fix": "red",
            "iterate": "blue",
        }

        for step in steps:
            step_type = step.get("step_type", "verify")
            status = step.get("test_status", "pending")
            content = step.get("content", "")

            status_icon = step_status_icons.get(status, "○")
            step_style = step_type_styles.get(step_type, "white")

            if status == "passed":
                status_style = "green"
            elif status == "failed":
                status_style = "red"
            elif status == "skipped":
                status_style = "dim"
            else:
                status_style = "white"

            step_text = Text()
            step_text.append(f"{status_icon} ", style=status_style)
            step_text.append(f"[{step_type}] ", style=step_style)
            step_text.append(content)

            await self.mount(Static(step_text, classes="task-detail-item"))

    async def _render_campaign_summary(self) -> None:
        """Render the full campaign summary view."""
        await self._clear_content()

        if not self._campaign_data:
            return

        campaign = self._campaign_data.get("campaign", {})
        progress = self._campaign_data.get("progress", {})
        research = self._campaign_data.get("research", [])

        name = campaign.get("name", "Unnamed Campaign")
        await self.mount(Static(name, classes="task-detail-title"))

        await self._render_campaign_metadata(campaign)
        await self._render_campaign_progress(progress)

        description = campaign.get("description", "")
        await self._render_section("DESCRIPTION", description)

        await self._render_campaign_research(research)

    async def _render_campaign_metadata(self, campaign: dict[str, Any]) -> None:
        """Render campaign metadata."""
        campaign_id = campaign.get("id", "")
        status = campaign.get("status", "unknown")
        priority = campaign.get("priority", "medium")
        created_at = campaign.get("created_at", "")
        updated_at = campaign.get("updated_at", "")

        priority_icon = PRIORITY_ICONS.get(priority, PRIORITY_ICONS["medium"])

        if campaign_id:
            id_row = Horizontal(classes="id-row")
            copy_button = Button("Copy", id="copy-campaign-id", classes="copy-id-button")
            id_text = Static(campaign_id, classes="id-text")
            id_row.compose_add_child(copy_button)
            id_row.compose_add_child(id_text)
            await self.mount(id_row)

        metadata_text = Text()

        metadata_text.append("Status: ")
        metadata_text.append(f"{status}\n")

        metadata_text.append(f"Priority: {priority_icon} {priority}\n")

        if created_at:
            date_str = str(created_at)[:10] if len(str(created_at)) >= 10 else created_at
            metadata_text.append(f"Created: {date_str}\n")

        if updated_at:
            date_str = str(updated_at)[:10] if len(str(updated_at)) >= 10 else updated_at
            metadata_text.append(f"Updated: {date_str}")

        await self.mount(Static(metadata_text, classes="task-detail-metadata"))

    async def _render_campaign_progress(self, progress: dict[str, Any]) -> None:
        """Render progress section with progress bar."""
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("PROGRESS", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        total = progress.get("total_tasks", 0)
        tasks_by_status = progress.get("tasks_by_status", {})
        done = tasks_by_status.get("done", 0)
        completion_rate = progress.get("completion_rate", 0.0)

        progress_text = Text()
        progress_text.append(f"Completion: {completion_rate}% ({done}/{total} tasks)\n")
        await self.mount(Static(progress_text, classes="task-detail-content"))

        from rich.progress_bar import ProgressBar

        progress_bar = ProgressBar(total=100, completed=completion_rate, width=35)
        await self.mount(Static(progress_bar, classes="task-detail-content"))

        status_text = Text()
        status_text.append("\nTasks by Status:\n")
        for status, count in tasks_by_status.items():
            icon = STATUS_ICONS.get(status, "○")
            color = RICH_STATUS_COLORS.get(status, "dim")
            status_text.append(f"  {icon} ", style=color)
            status_text.append(f"{status}: {count}\n")

        await self.mount(Static(status_text, classes="task-detail-content"))

    async def _render_campaign_research(self, research: list[dict[str, Any]]) -> None:
        """Render campaign research items grouped by type."""
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))
        await self.mount(Static("RESEARCH", classes="task-detail-section-header"))
        await self.mount(Static("═" * 40, classes="task-detail-section-divider"))

        if not research:
            await self.mount(Static("(No research items)", classes="task-detail-content"))
            return

        research_by_type: dict[str, list[dict[str, Any]]] = {}
        for item in research:
            item_type = item.get("type", "general")
            if item_type not in research_by_type:
                research_by_type[item_type] = []
            research_by_type[item_type].append(item)

        for research_type, items in research_by_type.items():
            type_header = Text()
            type_header.append(f"[{research_type}]", style="italic")
            await self.mount(Static(type_header, classes="task-detail-item-header"))

            for item in items:
                observations = item.get("observations", [])
                for obs in observations:
                    await self.mount(Static(f"  • {obs}", classes="task-detail-item", markup=False))

                notes = item.get("notes", "")
                if notes:
                    notes_text = Text()
                    notes_text.append("  Note: ", style="dim italic")
                    notes_text.append(notes, style="dim")
                    await self.mount(Static(notes_text, classes="task-detail-item"))

    @on(Button.Pressed, "#copy-campaign-id")
    def on_copy_campaign_id(self, event: Button.Pressed) -> None:
        """Handle click on campaign ID copy button."""
        if self._campaign_id:
            self.app.copy_to_clipboard(self._campaign_id)
            self.notify("Campaign ID copied to clipboard")

    @on(Button.Pressed, "#copy-task-id")
    def on_copy_task_id(self, event: Button.Pressed) -> None:
        """Handle click on task ID copy button."""
        if self._task_id:
            self.app.copy_to_clipboard(self._task_id)
            self.notify("Task ID copied to clipboard")

    @on(ClickableCriterion.CriterionClicked)
    def on_criterion_clicked(self, event: ClickableCriterion.CriterionClicked) -> None:
        """Handle criterion click by selecting it."""
        if event.criterion_index != self._selected_criterion_index:
            self._selected_criterion_index = event.criterion_index
            self._update_criterion_selection()

    def action_next_criterion(self) -> None:
        """Move selection to the next acceptance criterion."""
        if not self._criteria_data:
            return

        new_index = min(self._selected_criterion_index + 1, len(self._criteria_data) - 1)
        if new_index != self._selected_criterion_index:
            self._selected_criterion_index = new_index
            self._update_criterion_selection()

    def action_prev_criterion(self) -> None:
        """Move selection to the previous acceptance criterion."""
        if not self._criteria_data:
            return

        new_index = max(self._selected_criterion_index - 1, 0)
        if new_index != self._selected_criterion_index:
            self._selected_criterion_index = new_index
            self._update_criterion_selection()

    def _update_criterion_selection(self) -> None:
        """Update the visual selection highlighting for criteria."""
        for idx, widget_id in enumerate(self._criterion_widget_ids):
            try:
                widget = self.query_one(f"#{widget_id}", ClickableCriterion)
                if idx == self._selected_criterion_index:
                    widget.add_class("criteria-selected")
                else:
                    widget.remove_class("criteria-selected")
            except NoMatches:
                pass

    async def action_toggle_criterion(self) -> None:
        """Toggle the met status of the currently selected criterion."""
        if not self._criteria_data or self._selected_criterion_index < 0:
            return

        if self._selected_criterion_index >= len(self._criteria_data):
            return

        criterion = self._criteria_data[self._selected_criterion_index]
        entity_id = criterion.get("id")

        if not entity_id:
            self.notify("Cannot toggle: criterion has no ID", severity="error")
            return

        current_is_met = criterion.get("is_met", False)

        try:
            success = await self.data_service.toggle_criterion_met(
                criterion_entity_id=entity_id, is_met=not current_is_met
            )
            if success:
                criterion["is_met"] = not current_is_met
                await self._update_criterion_display()
            else:
                self.notify("Failed to update criterion", severity="error")
        except DataUpdateError as e:
            self.notify(f"Error: {e}", severity="error")
        except (NoMatches, KeyError, IndexError) as e:
            self.notify(f"Unexpected error: {e}", severity="error")

    async def _update_criterion_display(self) -> None:
        """Update the criterion display after a toggle."""
        if self._selected_criterion_index < 0:
            return

        idx = self._selected_criterion_index
        if idx >= len(self._criteria_data) or idx >= len(self._criterion_widget_ids):
            return

        criterion = self._criteria_data[idx]
        widget_id = self._criterion_widget_ids[idx]

        try:
            widget = self.query_one(f"#{widget_id}", ClickableCriterion)

            criterion_text = (
                criterion.get("content") or criterion.get("notes") or criterion.get("name", "")
            )
            is_met = criterion.get("is_met", False)

            crit_display = Text()
            if is_met:
                crit_display.append("[✓] ", style="green")
                crit_display.append(criterion_text)
            else:
                crit_display.append("[ ] ", style="dim")
                crit_display.append(criterion_text)

            widget.update(crit_display)
        except NoMatches:
            pass

        try:
            task_id_prefix = self._task_id[:8] if self._task_id else "unknown"
            progress_widget = self.query_one(f"#criteria-progress-{task_id_prefix}", Static)
            met_count = sum(1 for c in self._criteria_data if c.get("is_met", False))
            total_count = len(self._criteria_data)

            progress_text = Text()
            progress_text.append(f"Progress: {met_count}/{total_count} criteria met")
            progress_widget.update(progress_text)
        except NoMatches:
            pass
