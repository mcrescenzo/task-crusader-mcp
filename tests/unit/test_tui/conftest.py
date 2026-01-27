"""TUI-specific test fixtures and mocks.

This module provides fixtures for testing TUI widgets in isolation:
- mock_data_service: Mocked TUIDataService for isolated widget tests
- sample_task_data: Dict matching service output format with acceptance criteria
- sample_campaign_data: Dict matching campaign summary format
- sample_criteria: List of acceptance criteria with correct "id" field
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_criteria() -> list[dict[str, Any]]:
    """Sample acceptance criteria with correct 'id' field.

    This fixture provides criteria in the exact format returned by the service.
    IMPORTANT: The field is 'id', NOT 'entity_id'.
    """
    return [
        {
            "id": "criteria-uuid-001",
            "content": "Unit tests pass with 100% coverage",
            "is_met": False,
            "order_index": 0,
        },
        {
            "id": "criteria-uuid-002",
            "content": "Integration tests pass",
            "is_met": True,
            "order_index": 1,
        },
        {
            "id": "criteria-uuid-003",
            "content": "Code review approved",
            "is_met": False,
            "order_index": 2,
        },
    ]


@pytest.fixture
def sample_task_data(sample_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """Sample task data matching service output format.

    This fixture provides task data in the exact format returned by TaskService.get_task().
    """
    return {
        "id": "task-uuid-12345678",
        "title": "Implement TUI testing infrastructure",
        "description": "Create comprehensive test coverage for TUI widgets",
        "status": "in-progress",
        "priority": "high",
        "type": "code",
        "category": "testing",
        "campaign_id": "campaign-uuid-001",
        "dependencies": [],
        "dependency_details": [],
        "has_dependencies": False,
        "dependency_count": 0,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T12:00:00",
        "acceptance_criteria_details": sample_criteria,
        "research": [
            {
                "id": "research-uuid-001",
                "notes": "Textual provides Pilot for async testing",
                "association_type": "findings",
            }
        ],
        "implementation_notes": [
            {
                "id": "note-uuid-001",
                "notes": "Started with TaskDetailWidget tests",
                "note_type": "progress",
                "created_at": "2024-01-15T11:00:00",
            }
        ],
        "testing_steps": [],
    }


@pytest.fixture
def sample_task_with_dependencies() -> dict[str, Any]:
    """Sample task with dependencies for dependency testing."""
    return {
        "id": "task-uuid-blocked",
        "title": "Task with dependencies",
        "description": "This task depends on another task",
        "status": "pending",
        "priority": "medium",
        "type": "code",
        "campaign_id": "campaign-uuid-001",
        "dependencies": ["task-uuid-dep-001"],
        "dependency_details": [
            {
                "id": "task-uuid-dep-001",
                "title": "Dependency task",
                "status": "in-progress",
            }
        ],
        "has_dependencies": True,
        "dependency_count": 1,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T12:00:00",
        "acceptance_criteria_details": [],
        "research": [],
        "implementation_notes": [],
        "testing_steps": [],
    }


@pytest.fixture
def sample_campaign_data() -> dict[str, Any]:
    """Sample campaign data matching service output format.

    This fixture provides campaign data in the exact format returned by
    TUIDataService.get_campaign_summary().
    """
    return {
        "campaign": {
            "id": "campaign-uuid-001",
            "name": "TUI Testing Campaign",
            "description": "Comprehensive TUI test coverage implementation",
            "status": "active",
            "priority": "high",
            "created_at": "2024-01-10T09:00:00",
            "updated_at": "2024-01-15T12:00:00",
        },
        "progress": {
            "total_tasks": 10,
            "tasks_by_status": {
                "pending": 3,
                "in-progress": 2,
                "done": 4,
                "blocked": 1,
            },
            "completion_rate": 40.0,
        },
        "research": [
            {
                "id": "campaign-research-001",
                "type": "strategy",
                "observations": ["Use Textual Pilot for widget testing"],
                "notes": "Research finding",
            }
        ],
    }


@pytest.fixture
def sample_campaign_list() -> list[dict[str, Any]]:
    """Sample list of campaigns for CampaignListWidget testing."""
    return [
        {
            "id": "campaign-uuid-001",
            "name": "Active Campaign",
            "status": "active",
            "priority": "high",
            "task_count": 10,
            "done_count": 4,
        },
        {
            "id": "campaign-uuid-002",
            "name": "Planning Campaign",
            "status": "planning",
            "priority": "medium",
            "task_count": 5,
            "done_count": 0,
        },
        {
            "id": "campaign-uuid-003",
            "name": "Completed Campaign",
            "status": "completed",
            "priority": "low",
            "task_count": 8,
            "done_count": 8,
        },
    ]


@pytest.fixture
def sample_task_list() -> list[dict[str, Any]]:
    """Sample list of tasks for TaskDataTable testing."""
    return [
        {
            "id": "task-uuid-001",
            "title": "First task",
            "status": "pending",
            "priority": "high",
            "type": "code",
            "dependencies": [],
            "has_dependencies": False,
            "dependency_count": 0,
        },
        {
            "id": "task-uuid-002",
            "title": "Second task",
            "status": "in-progress",
            "priority": "medium",
            "type": "code",
            "dependencies": [],
            "has_dependencies": False,
            "dependency_count": 0,
        },
        {
            "id": "task-uuid-003",
            "title": "Third task - blocked",
            "status": "pending",
            "priority": "low",
            "type": "code",
            "dependencies": ["task-uuid-001"],
            "dependency_details": [
                {"id": "task-uuid-001", "title": "First task", "status": "pending"}
            ],
            "has_dependencies": True,
            "dependency_count": 1,
        },
        {
            "id": "task-uuid-004",
            "title": "Done task",
            "status": "done",
            "priority": "medium",
            "type": "code",
            "dependencies": [],
            "has_dependencies": False,
            "dependency_count": 0,
        },
    ]


@pytest.fixture
def mock_data_service(
    sample_task_data: dict[str, Any],
    sample_campaign_data: dict[str, Any],
    sample_task_list: list[dict[str, Any]],
    sample_campaign_list: list[dict[str, Any]],
) -> MagicMock:
    """Create a mocked TUIDataService for isolated widget tests.

    The mock is pre-configured with sample data for common operations.
    Individual tests can override specific methods as needed.
    """
    mock = MagicMock()

    # Configure async methods
    mock.get_task_detail = AsyncMock(return_value=sample_task_data)
    mock.get_tasks = AsyncMock(return_value=sample_task_list)
    mock.get_campaigns = AsyncMock(return_value=sample_campaign_list)
    mock.get_campaign_summary = AsyncMock(return_value=sample_campaign_data)
    mock.toggle_criterion_met = AsyncMock(return_value=True)
    mock.update_task_status = AsyncMock(return_value=True)
    mock.update_task_priority = AsyncMock(return_value=True)
    mock.delete_task = AsyncMock(return_value=True)
    mock.delete_campaign = AsyncMock(return_value=True)
    mock.get_campaign_task_count = AsyncMock(return_value=5)
    mock.create_task = AsyncMock(
        return_value={
            "id": "new-task-uuid",
            "title": "New task",
            "status": "pending",
            "priority": "medium",
        }
    )
    mock.create_campaign = AsyncMock(
        return_value={
            "id": "new-campaign-uuid",
            "name": "New Campaign",
            "status": "planning",
            "priority": "medium",
        }
    )
    mock.bulk_delete_tasks = AsyncMock(return_value=True)
    mock.bulk_update_task_status = AsyncMock(return_value=True)
    mock.bulk_update_task_priority = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def mock_config_service() -> MagicMock:
    """Create a mocked TUIConfigService for isolated widget tests."""
    mock = MagicMock()
    mock.get_status_filter.return_value = "all"
    mock.get_campaign_filter.return_value = "all"
    mock.set_status_filter = MagicMock()
    mock.set_campaign_filter = MagicMock()
    return mock
