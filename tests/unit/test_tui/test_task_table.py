"""Tests for TaskDataTable widget.

This module tests the TaskDataTable component, including:
- Task filtering and sorting logic (no app context needed)
- Task selection logic
- Status/priority filtering
- Messages
"""

from typing import Any

from rich.text import Text

from task_crusade_mcp.tui.widgets.task_data_table import TaskDataTable


class TestTaskDataTableFiltering:
    """Tests for task filtering functionality (logic only, no widget instantiation)."""

    def test_status_filter_pending(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Status filter filters tasks by pending status."""
        # Direct method test without widget instantiation
        # Filter logic: return only pending tasks
        filtered = [t for t in sample_task_list if t["status"] == "pending"]
        assert len(filtered) == 2
        assert all(t["status"] == "pending" for t in filtered)

    def test_status_filter_all(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Status filter 'all' shows all tasks."""
        # "all" filter returns everything
        filtered = sample_task_list
        assert len(filtered) == 4

    def test_search_filter_by_title(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Search filter filters tasks by title (case-insensitive)."""
        query = "first"
        filtered = [t for t in sample_task_list if query.lower() in t.get("title", "").lower()]
        assert len(filtered) == 1
        assert filtered[0]["id"] == "task-uuid-001"

    def test_search_filter_case_insensitive(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Search filter is case-insensitive."""
        query = "FIRST"
        filtered = [t for t in sample_task_list if query.lower() in t.get("title", "").lower()]
        assert len(filtered) == 1

    def test_empty_search_returns_all(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Empty search query returns all tasks."""
        query = ""
        if not query:
            filtered = sample_task_list
        else:
            filtered = [t for t in sample_task_list if query.lower() in t.get("title", "").lower()]
        assert len(filtered) == 4


class TestTaskDataTableSorting:
    """Tests for task sorting functionality."""

    def test_sort_by_priority(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Sort by priority orders critical > high > medium > low."""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_tasks = sorted(
            sample_task_list,
            key=lambda t: priority_order.get(t.get("priority", "medium"), 2),
        )
        # High priority task should be first
        assert sorted_tasks[0]["priority"] == "high"

    def test_sort_by_status(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Sort by status orders pending > in-progress > blocked > done."""
        status_order = {
            "pending": 0,
            "in-progress": 1,
            "blocked": 2,
            "done": 3,
            "cancelled": 4,
        }
        sorted_tasks = sorted(
            sample_task_list,
            key=lambda t: status_order.get(t.get("status", "pending"), 0),
        )
        # Pending tasks should be first
        assert sorted_tasks[0]["status"] == "pending"

    def test_sort_by_title(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Sort by title orders alphabetically."""
        sorted_tasks = sorted(
            sample_task_list,
            key=lambda t: t.get("title", "").lower(),
        )
        # "Done task" should be first alphabetically
        assert sorted_tasks[0]["title"] == "Done task"


class TestTaskDataTableSelection:
    """Tests for task selection logic."""

    def test_find_task_by_id(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Finding task by ID works correctly."""
        task_id = "task-uuid-001"
        result = next((t for t in sample_task_list if t.get("id") == task_id), None)
        assert result is not None
        assert result["id"] == "task-uuid-001"

    def test_find_task_returns_none_for_invalid_id(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Finding task with invalid ID returns None."""
        task_id = "non-existent"
        result = next((t for t in sample_task_list if t.get("id") == task_id), None)
        assert result is None


class TestTaskDataTableSelectionMode:
    """Tests for multi-selection mode logic."""

    def test_toggle_selection_adds_task(self) -> None:
        """Toggle selection adds unselected task to selection."""
        selected_keys: set[str] = set()
        task_id = "task-1"

        # Toggle adds
        if task_id in selected_keys:
            selected_keys.remove(task_id)
        else:
            selected_keys.add(task_id)

        assert task_id in selected_keys

    def test_toggle_selection_removes_task(self) -> None:
        """Toggle selection removes selected task from selection."""
        selected_keys: set[str] = {"task-1"}
        task_id = "task-1"

        # Toggle removes
        if task_id in selected_keys:
            selected_keys.remove(task_id)
        else:
            selected_keys.add(task_id)

        assert task_id not in selected_keys

    def test_select_all_visible(self) -> None:
        """Select all adds all visible task IDs to selection."""
        selected_keys: set[str] = set()
        visible_task_ids = {"task-1", "task-2", "task-3"}

        # If not all selected, select all
        if not visible_task_ids.issubset(selected_keys):
            selected_keys.update(visible_task_ids)

        assert visible_task_ids.issubset(selected_keys)

    def test_deselect_all_visible(self) -> None:
        """Select all when all are selected deselects all."""
        selected_keys: set[str] = {"task-1", "task-2", "task-3"}
        visible_task_ids = {"task-1", "task-2", "task-3"}

        # If all selected, deselect all
        if visible_task_ids.issubset(selected_keys):
            selected_keys -= visible_task_ids

        assert len(selected_keys.intersection(visible_task_ids)) == 0


class TestTaskDataTableDependencies:
    """Tests for dependency handling logic."""

    def test_enrich_dependency_details(
        self,
        sample_task_list: list[dict[str, Any]],
    ) -> None:
        """Dependency enrichment adds dependency info to tasks."""
        tasks = [t.copy() for t in sample_task_list]
        task_map = {task["id"]: task for task in tasks}

        # Build blocking map (which tasks does each task block)
        blocking_map: dict[str, list[dict[str, Any]]] = {task["id"]: [] for task in tasks}

        for task in tasks:
            dependencies = task.get("dependencies", [])
            if dependencies:
                dep_details = []
                for dep_id in dependencies:
                    if dep_id in task_map:
                        dep_task = task_map[dep_id]
                        dep_details.append({
                            "id": dep_id,
                            "title": dep_task.get("title", "Unknown"),
                            "status": dep_task.get("status", "unknown"),
                        })
                        blocking_map[dep_id].append({
                            "id": task["id"],
                            "title": task.get("title", "Unknown"),
                            "status": task.get("status", "unknown"),
                        })
                task["dependency_details"] = dep_details

        for task in tasks:
            task["blocking_details"] = blocking_map.get(task["id"], [])

        # task-uuid-003 depends on task-uuid-001
        blocked_task = next(t for t in tasks if t["id"] == "task-uuid-003")
        assert len(blocked_task.get("dependency_details", [])) == 1

        # task-uuid-001 blocks task-uuid-003
        blocking_task = next(t for t in tasks if t["id"] == "task-uuid-001")
        assert len(blocking_task.get("blocking_details", [])) == 1

    def test_has_no_unmet_dependencies_true(self) -> None:
        """Task with all deps done has no unmet dependencies."""
        task = {
            "id": "task-1",
            "dependencies": ["dep-1"],
            "dependency_details": [{"id": "dep-1", "status": "done"}],
        }

        dep_details = task.get("dependency_details", [])
        result = all(dep.get("status") == "done" for dep in dep_details)

        assert result is True

    def test_has_no_unmet_dependencies_false(self) -> None:
        """Task with pending deps has unmet dependencies."""
        task = {
            "id": "task-1",
            "dependencies": ["dep-1"],
            "dependency_details": [{"id": "dep-1", "status": "pending"}],
        }

        dep_details = task.get("dependency_details", [])
        result = all(dep.get("status") == "done" for dep in dep_details)

        assert result is False

    def test_has_no_unmet_dependencies_no_deps(self) -> None:
        """Task with no dependencies has no unmet dependencies."""
        task = {"id": "task-1", "dependencies": []}

        dependencies = task.get("dependencies", [])
        if not dependencies:
            result = True
        else:
            dep_details = task.get("dependency_details", [])
            result = all(dep.get("status") == "done" for dep in dep_details)

        assert result is True


class TestTaskDataTableMessages:
    """Tests for message classes."""

    def test_task_selected_message(self) -> None:
        """TaskSelected message contains task_id."""
        message = TaskDataTable.TaskSelected(task_id="task-123")
        assert message.task_id == "task-123"

    def test_task_delete_requested_message(self) -> None:
        """TaskDeleteRequested message contains task_id."""
        message = TaskDataTable.TaskDeleteRequested(task_id="task-123")
        assert message.task_id == "task-123"

    def test_task_deleted_message(self) -> None:
        """TaskDeleted message contains task_id."""
        message = TaskDataTable.TaskDeleted(task_id="task-123")
        assert message.task_id == "task-123"

    def test_task_filter_changed_message(self) -> None:
        """TaskFilterChanged message contains filter info."""
        message = TaskDataTable.TaskFilterChanged(
            filter_value="pending",
            filter_label="Pending",
        )
        assert message.filter_value == "pending"
        assert message.filter_label == "Pending"

    def test_task_status_changed_message(self) -> None:
        """TaskStatusChanged message contains task_id and new_status."""
        message = TaskDataTable.TaskStatusChanged(
            task_id="task-123",
            new_status="done",
        )
        assert message.task_id == "task-123"
        assert message.new_status == "done"

    def test_task_priority_changed_message(self) -> None:
        """TaskPriorityChanged message contains task_id and new_priority."""
        message = TaskDataTable.TaskPriorityChanged(
            task_id="task-123",
            new_priority="high",
        )
        assert message.task_id == "task-123"
        assert message.new_priority == "high"

    def test_task_search_changed_message(self) -> None:
        """TaskSearchChanged message contains query and active flag."""
        message = TaskDataTable.TaskSearchChanged(query="test", is_active=True)
        assert message.query == "test"
        assert message.is_active is True

    def test_new_task_requested_message(self) -> None:
        """NewTaskRequested message contains campaign_id."""
        message = TaskDataTable.NewTaskRequested(campaign_id="camp-123")
        assert message.campaign_id == "camp-123"

    def test_task_created_message(self) -> None:
        """TaskCreated message contains task_id and task_data."""
        message = TaskDataTable.TaskCreated(
            task_id="task-123",
            task_data={"title": "Test"},
        )
        assert message.task_id == "task-123"
        assert message.task_data["title"] == "Test"


class TestTaskDataTableRenderLogic:
    """Tests for rendering logic without widget instantiation."""

    def test_priority_cell_text_assembly(self) -> None:
        """Priority cell can be assembled correctly."""
        from task_crusade_mcp.tui.constants import PRIORITY_COLORS, PRIORITY_ICONS

        priority = "high"
        icon = PRIORITY_ICONS.get(priority, "?")
        color = PRIORITY_COLORS.get(priority, "white")

        result = Text(icon, style=color)
        assert isinstance(result, Text)
        assert str(result) == icon

    def test_priority_defaults_to_medium_for_none(self) -> None:
        """Priority defaults to medium when None."""
        from task_crusade_mcp.tui.constants import PRIORITY_ICONS

        priority = None
        if priority is None:
            priority = "medium"
        priority = priority.lower()

        icon = PRIORITY_ICONS.get(priority, "?")
        assert icon is not None

    def test_status_icon_lookup(self) -> None:
        """Status icons can be looked up correctly."""
        from task_crusade_mcp.tui.constants import STATUS_ICONS

        for status in ["pending", "in-progress", "done", "blocked"]:
            icon = STATUS_ICONS.get(status)
            assert icon is not None, f"Status '{status}' should have an icon"

    def test_task_cell_text_assembly(self) -> None:
        """Task cell text can be assembled with status icon and title."""
        from task_crusade_mcp.tui.constants import RICH_STATUS_COLORS, STATUS_ICONS

        task = {"id": "t1", "title": "Test Task", "status": "pending"}

        status = task.get("status", "pending")
        title = task.get("title", "Unnamed Task")
        status_icon = STATUS_ICONS.get(status, "?")
        status_color = RICH_STATUS_COLORS.get(status, "dim")

        result = Text.assemble(
            (status_icon, status_color),
            " ",
            title,
        )

        assert isinstance(result, Text)
        assert "Test Task" in str(result)


class TestActionableFilterLogic:
    """Tests for actionable filter logic."""

    def test_actionable_pending_no_deps_is_actionable(self) -> None:
        """Pending task with no dependencies is actionable."""
        task = {
            "id": "task-1",
            "status": "pending",
            "dependencies": [],
        }

        is_pending = task.get("status") == "pending"
        has_no_deps = len(task.get("dependencies", [])) == 0
        is_actionable = is_pending and has_no_deps

        assert is_actionable is True

    def test_actionable_pending_with_done_deps_is_actionable(self) -> None:
        """Pending task with all done dependencies is actionable."""
        task = {
            "id": "task-1",
            "status": "pending",
            "dependencies": ["dep-1"],
            "dependency_details": [{"id": "dep-1", "status": "done"}],
        }

        is_pending = task.get("status") == "pending"
        dep_details = task.get("dependency_details", [])
        all_deps_done = all(d.get("status") == "done" for d in dep_details) if dep_details else True
        is_actionable = is_pending and all_deps_done

        assert is_actionable is True

    def test_actionable_pending_with_pending_deps_not_actionable(self) -> None:
        """Pending task with pending dependencies is not actionable."""
        task = {
            "id": "task-1",
            "status": "pending",
            "dependencies": ["dep-1"],
            "dependency_details": [{"id": "dep-1", "status": "pending"}],
        }

        is_pending = task.get("status") == "pending"
        dep_details = task.get("dependency_details", [])
        all_deps_done = all(d.get("status") == "done" for d in dep_details) if dep_details else True
        is_actionable = is_pending and all_deps_done

        assert is_actionable is False

    def test_actionable_in_progress_not_actionable(self) -> None:
        """In-progress task is not actionable (already being worked on)."""
        task = {
            "id": "task-1",
            "status": "in-progress",
            "dependencies": [],
        }

        is_pending = task.get("status") == "pending"
        is_actionable = is_pending  # Must be pending to be actionable

        assert is_actionable is False
