"""
Dependency Validator - Task dependency graph validation and ordering.

Provides validation of task dependency graphs including:
- Reference validation (all temp_ids must exist)
- Cycle detection (no circular dependencies)
- Topological sorting (correct creation order)
"""

from collections import deque
from typing import Dict, List, Set

from task_crusade_mcp.domain.entities.campaign_spec import TaskSpec
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)


class DependencyValidator:
    """
    Validates task dependency graphs.

    Implements:
    1. Reference validation - ensures all dependency temp_ids exist
    2. Cycle detection - uses three-color DFS algorithm
    3. Topological sorting - uses Kahn's algorithm
    """

    def __init__(self, tasks: List[TaskSpec]):
        """
        Initialize validator with task specifications.

        Args:
            tasks: List of TaskSpec objects to validate.
        """
        self.tasks = tasks
        self._temp_id_to_task: Dict[str, TaskSpec] = {t.temp_id: t for t in tasks}
        self._temp_id_to_index: Dict[str, int] = {t.temp_id: i for i, t in enumerate(tasks)}

    def validate_references(self) -> List[str]:
        """
        Validate that all dependency temp_ids exist.

        Returns:
            List of error messages for invalid references.
        """
        errors = []
        valid_temp_ids = set(self._temp_id_to_task.keys())

        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in valid_temp_ids:
                    errors.append(
                        f"Task '{task.temp_id}' ('{task.title}') depends on "
                        f"'{dep_id}' which doesn't exist. "
                        f"Available temp_ids: {sorted(valid_temp_ids)}"
                    )

        return errors

    def validate_temp_ids(self) -> List[str]:
        """
        Validate temp_id uniqueness and presence.

        Returns:
            List of error messages for invalid temp_ids.
        """
        errors = []
        seen_ids: Set[str] = set()

        for i, task in enumerate(self.tasks):
            if not task.temp_id:
                errors.append(f"Task at index {i} ('{task.title}') missing required 'temp_id'")
            elif task.temp_id in seen_ids:
                errors.append(f"Duplicate temp_id: '{task.temp_id}'")
            else:
                seen_ids.add(task.temp_id)

        return errors

    def detect_cycles(self) -> List[str]:
        """
        Detect cycles using three-color DFS algorithm.

        Colors:
        - 0 (White): Unvisited
        - 1 (Gray): Currently visiting (in recursion stack)
        - 2 (Black): Finished visiting

        Returns:
            List of error messages describing cycles found.
        """
        errors = []
        colors: Dict[str, int] = {t.temp_id: 0 for t in self.tasks}
        parent: Dict[str, str] = {}

        def dfs(node: str) -> bool:
            """DFS traversal returning True if cycle found."""
            colors[node] = 1  # Mark gray (visiting)

            task = self._temp_id_to_task.get(node)
            if not task:
                return False

            for neighbor in task.dependencies:
                if neighbor not in colors:
                    continue  # Invalid reference, handled elsewhere

                if colors[neighbor] == 1:  # Gray - cycle found
                    # Build cycle path
                    cycle_path = [neighbor]
                    current = node
                    while current != neighbor:
                        cycle_path.append(current)
                        current = parent.get(current, neighbor)
                    cycle_path.append(neighbor)
                    cycle_path.reverse()

                    # Build readable error with task titles
                    cycle_str = " -> ".join(
                        f"{tid} ('{self._temp_id_to_task[tid].title}')" for tid in cycle_path
                    )
                    errors.append(f"Circular dependency detected: {cycle_str}")
                    return True

                if colors[neighbor] == 0:  # White - unvisited
                    parent[neighbor] = node
                    if dfs(neighbor):
                        return True

            colors[node] = 2  # Mark black (finished)
            return False

        # Start DFS from each unvisited node
        for task in self.tasks:
            if colors[task.temp_id] == 0 and dfs(task.temp_id):
                break  # Stop after first cycle found

        return errors

    def get_topological_order(self) -> List[str]:
        """
        Get topological order using Kahn's algorithm.

        Returns tasks in order such that dependencies come before dependents.

        Returns:
            List of temp_ids in topological order.

        Raises:
            ValueError: If graph has cycles (should detect with detect_cycles first).
        """
        # Calculate in-degrees (number of dependencies)
        in_degree: Dict[str, int] = {t.temp_id: len(t.dependencies) for t in self.tasks}

        # Filter to only valid dependencies
        for task in self.tasks:
            valid_deps = [d for d in task.dependencies if d in self._temp_id_to_task]
            in_degree[task.temp_id] = len(valid_deps)

        # Initialize queue with nodes having no dependencies
        queue = deque([tid for tid, degree in in_degree.items() if degree == 0])
        result: List[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # Reduce in-degree of dependents
            for task in self.tasks:
                if node in task.dependencies:
                    in_degree[task.temp_id] -= 1
                    if in_degree[task.temp_id] == 0:
                        queue.append(task.temp_id)

        # If result doesn't contain all nodes, there's a cycle
        if len(result) != len(self.tasks):
            raise ValueError(
                "Graph contains a cycle. Run detect_cycles() first for detailed error."
            )

        return result

    def validate(self) -> DomainResult[List[str]]:
        """
        Perform full validation and return topological order.

        Validates:
        1. All temp_ids are present and unique
        2. All dependency references are valid
        3. No circular dependencies exist

        Returns:
            DomainResult containing:
            - On success: List of temp_ids in topological order
            - On failure: Error messages describing validation failures
        """
        all_errors: List[str] = []

        # Step 1: Validate temp_ids
        temp_id_errors = self.validate_temp_ids()
        if temp_id_errors:
            all_errors.extend(temp_id_errors)
            # Can't continue if temp_ids are invalid
            return DomainError.validation_error(
                message="Invalid task temp_ids",
                details={"errors": all_errors},
            )

        # Step 2: Validate references
        ref_errors = self.validate_references()
        all_errors.extend(ref_errors)

        # Step 3: Detect cycles (only if references are valid)
        if not ref_errors:
            cycle_errors = self.detect_cycles()
            all_errors.extend(cycle_errors)

        # Return errors if any
        if all_errors:
            return DomainError.validation_error(
                message="Dependency validation failed",
                details={"errors": all_errors},
            )

        # Get topological order
        try:
            order = self.get_topological_order()
            return DomainSuccess.create(data=order)
        except ValueError as e:
            return DomainError.validation_error(
                message="Failed to determine task creation order",
                details={"reason": str(e)},
            )
