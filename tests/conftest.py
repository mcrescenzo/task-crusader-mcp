"""Pytest configuration and fixtures."""

import contextlib
import os
import shutil
import tempfile
from typing import Generator

import pytest

from task_crusade_mcp.database.orm_manager import ORMManager, reset_orm_manager
from task_crusade_mcp.services.service_factory import reset_service_factory


@pytest.fixture(scope="function", autouse=True)
def reset_singletons():
    """Reset singletons and set up test database before each test."""
    # Create a unique temp database for this test
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")

    # Store old env var
    old_db_path = os.environ.get("CRUSADER_DB_PATH")

    # Set env var BEFORE resetting singletons
    os.environ["CRUSADER_DB_PATH"] = db_path

    # Now reset singletons - they will pick up the test database path
    reset_orm_manager()
    reset_service_factory()

    yield

    # Cleanup after test
    reset_orm_manager()
    reset_service_factory()

    # Restore old env var
    if old_db_path is not None:
        os.environ["CRUSADER_DB_PATH"] = old_db_path
    elif "CRUSADER_DB_PATH" in os.environ:
        del os.environ["CRUSADER_DB_PATH"]

    # Clean up temp directory
    with contextlib.suppress(Exception):
        shutil.rmtree(tmpdir)


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Get the test database path."""
    # Return the path set by reset_singletons fixture
    yield os.environ["CRUSADER_DB_PATH"]


@pytest.fixture
def orm_manager(temp_db_path: str) -> Generator[ORMManager, None, None]:
    """Create an ORM manager with a temporary database."""
    manager = ORMManager(temp_db_path)
    yield manager
    manager.close()


@pytest.fixture
def campaign_repo(orm_manager: ORMManager):
    """Create a campaign repository."""
    from task_crusade_mcp.database.repositories import CampaignRepository

    return CampaignRepository(orm_manager)


@pytest.fixture
def task_repo(orm_manager: ORMManager):
    """Create a task repository."""
    from task_crusade_mcp.database.repositories import TaskRepository

    return TaskRepository(orm_manager)


@pytest.fixture
def hint_generator():
    """Create a hint generator."""
    from task_crusade_mcp.services import HintGenerator

    return HintGenerator(enabled=True)


@pytest.fixture
def campaign_service(orm_manager: ORMManager, hint_generator):
    """Create a campaign service with all dependencies."""
    from task_crusade_mcp.database.repositories import (
        CampaignRepository,
        MemoryAssociationRepository,
        MemoryEntityRepository,
        MemorySessionRepository,
        TaskRepository,
    )
    from task_crusade_mcp.services import CampaignService

    return CampaignService(
        campaign_repo=CampaignRepository(orm_manager),
        task_repo=TaskRepository(orm_manager),
        memory_session_repo=MemorySessionRepository(orm_manager),
        memory_entity_repo=MemoryEntityRepository(orm_manager),
        memory_association_repo=MemoryAssociationRepository(orm_manager),
        hint_generator=hint_generator,
    )


@pytest.fixture
def task_service(orm_manager: ORMManager, hint_generator):
    """Create a task service with all dependencies."""
    from task_crusade_mcp.database.repositories import (
        CampaignRepository,
        MemoryAssociationRepository,
        MemoryEntityRepository,
        MemorySessionRepository,
        TaskRepository,
    )
    from task_crusade_mcp.services import TaskService

    return TaskService(
        task_repo=TaskRepository(orm_manager),
        campaign_repo=CampaignRepository(orm_manager),
        memory_session_repo=MemorySessionRepository(orm_manager),
        memory_entity_repo=MemoryEntityRepository(orm_manager),
        memory_association_repo=MemoryAssociationRepository(orm_manager),
        hint_generator=hint_generator,
    )
