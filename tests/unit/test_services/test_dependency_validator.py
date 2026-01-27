"""Unit tests for DependencyValidator."""

import pytest

from task_crusade_mcp.domain.entities.campaign_spec import TaskSpec
from task_crusade_mcp.services.dependency_validator import DependencyValidator


class TestDependencyValidator:
    """Tests for DependencyValidator class."""

    # --- Fixtures ---

    def _make_task(
        self,
        temp_id: str,
        title: str = "",
        dependencies: list = None,
    ) -> TaskSpec:
        """Helper to create TaskSpec."""
        return TaskSpec(
            temp_id=temp_id,
            title=title or f"Task {temp_id}",
            dependencies=dependencies or [],
        )

    # --- validate_temp_ids Tests ---

    def test_validate_temp_ids_all_valid(self):
        """Test that valid temp_ids pass validation."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2"),
            self._make_task("t3"),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_temp_ids()

        assert errors == []

    def test_validate_temp_ids_missing(self):
        """Test that missing temp_id is detected."""
        tasks = [
            TaskSpec(temp_id="", title="Task 1"),
            self._make_task("t2"),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_temp_ids()

        assert len(errors) == 1
        assert "missing required 'temp_id'" in errors[0]

    def test_validate_temp_ids_duplicate(self):
        """Test that duplicate temp_ids are detected."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t1"),  # Duplicate
            self._make_task("t2"),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_temp_ids()

        assert len(errors) == 1
        assert "Duplicate temp_id: 't1'" in errors[0]

    # --- validate_references Tests ---

    def test_validate_references_all_valid(self):
        """Test that valid references pass validation."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t3", dependencies=["t1", "t2"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_references()

        assert errors == []

    def test_validate_references_invalid_reference(self):
        """Test that invalid references are detected."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t99"]),  # Invalid
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_references()

        assert len(errors) == 1
        assert "t99" in errors[0]
        assert "doesn't exist" in errors[0]

    def test_validate_references_multiple_invalid(self):
        """Test that multiple invalid references are all detected."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t99", "t100"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.validate_references()

        assert len(errors) == 2

    # --- detect_cycles Tests ---

    def test_detect_cycles_no_cycle(self):
        """Test that valid DAG passes cycle detection."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t3", dependencies=["t1", "t2"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.detect_cycles()

        assert errors == []

    def test_detect_cycles_simple_cycle(self):
        """Test that simple 2-node cycle is detected."""
        tasks = [
            self._make_task("t1", "Task 1", dependencies=["t2"]),
            self._make_task("t2", "Task 2", dependencies=["t1"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.detect_cycles()

        assert len(errors) == 1
        assert "Circular dependency" in errors[0]

    def test_detect_cycles_three_node_cycle(self):
        """Test that 3-node cycle is detected."""
        tasks = [
            self._make_task("t1", "Task 1", dependencies=["t3"]),
            self._make_task("t2", "Task 2", dependencies=["t1"]),
            self._make_task("t3", "Task 3", dependencies=["t2"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.detect_cycles()

        assert len(errors) == 1
        assert "Circular dependency" in errors[0]
        # Should include task titles
        assert "Task" in errors[0]

    def test_detect_cycles_self_reference(self):
        """Test that self-reference is detected as cycle."""
        tasks = [
            self._make_task("t1", "Task 1", dependencies=["t1"]),
        ]
        validator = DependencyValidator(tasks)

        errors = validator.detect_cycles()

        assert len(errors) == 1
        assert "Circular dependency" in errors[0]

    # --- get_topological_order Tests ---

    def test_topological_order_simple(self):
        """Test topological order for simple chain."""
        tasks = [
            self._make_task("t3", dependencies=["t2"]),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t1"),
        ]
        validator = DependencyValidator(tasks)

        order = validator.get_topological_order()

        # t1 must come before t2, t2 must come before t3
        assert order.index("t1") < order.index("t2")
        assert order.index("t2") < order.index("t3")

    def test_topological_order_diamond(self):
        """Test topological order for diamond dependency pattern."""
        #     t1
        #    /  \
        #   t2  t3
        #    \  /
        #     t4
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t3", dependencies=["t1"]),
            self._make_task("t4", dependencies=["t2", "t3"]),
        ]
        validator = DependencyValidator(tasks)

        order = validator.get_topological_order()

        # t1 must come before t2 and t3
        assert order.index("t1") < order.index("t2")
        assert order.index("t1") < order.index("t3")
        # t2 and t3 must come before t4
        assert order.index("t2") < order.index("t4")
        assert order.index("t3") < order.index("t4")

    def test_topological_order_no_dependencies(self):
        """Test topological order when no dependencies exist."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2"),
            self._make_task("t3"),
        ]
        validator = DependencyValidator(tasks)

        order = validator.get_topological_order()

        # All tasks should be in the result
        assert set(order) == {"t1", "t2", "t3"}

    def test_topological_order_raises_on_cycle(self):
        """Test that get_topological_order raises on cycle."""
        tasks = [
            self._make_task("t1", dependencies=["t2"]),
            self._make_task("t2", dependencies=["t1"]),
        ]
        validator = DependencyValidator(tasks)

        with pytest.raises(ValueError, match="cycle"):
            validator.get_topological_order()

    # --- validate (Full Validation) Tests ---

    def test_validate_success(self):
        """Test full validation success returns topological order."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t3", dependencies=["t1", "t2"]),
        ]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_success
        assert result.data is not None
        # Should return topological order
        assert result.data.index("t1") < result.data.index("t2")
        assert result.data.index("t2") < result.data.index("t3")

    def test_validate_fails_on_missing_temp_id(self):
        """Test full validation fails on missing temp_id."""
        tasks = [
            TaskSpec(temp_id="", title="Task 1"),
            self._make_task("t2"),
        ]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_failure
        assert "Invalid task temp_ids" in (result.error_message or "")

    def test_validate_fails_on_invalid_reference(self):
        """Test full validation fails on invalid reference."""
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t99"]),
        ]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_failure
        assert "Dependency validation failed" in (result.error_message or "")

    def test_validate_fails_on_cycle(self):
        """Test full validation fails on cycle."""
        tasks = [
            self._make_task("t1", dependencies=["t2"]),
            self._make_task("t2", dependencies=["t1"]),
        ]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_failure
        assert "Dependency validation failed" in (result.error_message or "")

    # --- Edge Cases ---

    def test_empty_task_list(self):
        """Test validation of empty task list."""
        validator = DependencyValidator([])

        result = validator.validate()

        assert result.is_success
        assert result.data == []

    def test_single_task_no_dependencies(self):
        """Test single task with no dependencies."""
        tasks = [self._make_task("t1")]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_success
        assert result.data == ["t1"]

    def test_many_tasks_complex_graph(self):
        """Test complex dependency graph with many tasks."""
        # Create a more complex graph:
        # t1 -> t2 -> t4 -> t6
        #   \-> t3 -> t5 -/
        tasks = [
            self._make_task("t1"),
            self._make_task("t2", dependencies=["t1"]),
            self._make_task("t3", dependencies=["t1"]),
            self._make_task("t4", dependencies=["t2"]),
            self._make_task("t5", dependencies=["t3"]),
            self._make_task("t6", dependencies=["t4", "t5"]),
        ]
        validator = DependencyValidator(tasks)

        result = validator.validate()

        assert result.is_success
        order = result.data
        # Verify ordering constraints
        assert order.index("t1") < order.index("t2")
        assert order.index("t1") < order.index("t3")
        assert order.index("t2") < order.index("t4")
        assert order.index("t3") < order.index("t5")
        assert order.index("t4") < order.index("t6")
        assert order.index("t5") < order.index("t6")
