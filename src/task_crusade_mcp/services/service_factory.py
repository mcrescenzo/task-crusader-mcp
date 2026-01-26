"""
Service Factory - Dependency injection for services.

Provides a centralized factory for creating service instances with
proper dependency injection.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager

if TYPE_CHECKING:
    from task_crusade_mcp.services.campaign_service import CampaignService
    from task_crusade_mcp.services.task_service import TaskService
from task_crusade_mcp.database.repositories import (
    CampaignRepository,
    MemoryAssociationRepository,
    MemoryEntityRepository,
    MemorySessionRepository,
    TaskRepository,
)

# Module-level singleton
_global_factory: Optional["ServiceFactory"] = None
_global_lock = threading.Lock()


def get_service_factory(orm_manager: Optional[ORMManager] = None) -> "ServiceFactory":
    """
    Get the singleton service factory instance.

    Args:
        orm_manager: Optional ORM manager instance. Uses singleton if not provided.

    Returns:
        ServiceFactory singleton instance.
    """
    global _global_factory

    with _global_lock:
        if _global_factory is None:
            _global_factory = ServiceFactory(orm_manager)
        return _global_factory


def reset_service_factory() -> None:
    """Reset the global service factory (for testing)."""
    global _global_factory

    with _global_lock:
        _global_factory = None


class ServiceFactory:
    """
    Factory for creating service instances with dependency injection.

    Creates and caches service instances, ensuring they share the same
    ORM manager and repositories.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """
        Initialize the service factory.

        Args:
            orm_manager: ORM manager instance. Uses singleton if not provided.
        """
        self._orm_manager = orm_manager or get_orm_manager()
        self._lock = threading.RLock()  # RLock allows reentrant locking

        # Repository cache
        self._campaign_repo: Optional[CampaignRepository] = None
        self._task_repo: Optional[TaskRepository] = None
        self._memory_session_repo: Optional[MemorySessionRepository] = None
        self._memory_entity_repo: Optional[MemoryEntityRepository] = None
        self._memory_association_repo: Optional[MemoryAssociationRepository] = None

        # Service cache
        self._campaign_service: Optional["CampaignService"] = None
        self._task_service: Optional["TaskService"] = None

    @property
    def orm_manager(self) -> ORMManager:
        """Get the ORM manager."""
        return self._orm_manager

    # Repository getters
    def get_campaign_repository(self) -> CampaignRepository:
        """Get or create the campaign repository."""
        with self._lock:
            if self._campaign_repo is None:
                self._campaign_repo = CampaignRepository(self._orm_manager)
            return self._campaign_repo

    def get_task_repository(self) -> TaskRepository:
        """Get or create the task repository."""
        with self._lock:
            if self._task_repo is None:
                self._task_repo = TaskRepository(self._orm_manager)
            return self._task_repo

    def get_memory_session_repository(self) -> MemorySessionRepository:
        """Get or create the memory session repository."""
        with self._lock:
            if self._memory_session_repo is None:
                self._memory_session_repo = MemorySessionRepository(self._orm_manager)
            return self._memory_session_repo

    def get_memory_entity_repository(self) -> MemoryEntityRepository:
        """Get or create the memory entity repository."""
        with self._lock:
            if self._memory_entity_repo is None:
                self._memory_entity_repo = MemoryEntityRepository(self._orm_manager)
            return self._memory_entity_repo

    def get_memory_association_repository(self) -> MemoryAssociationRepository:
        """Get or create the memory association repository."""
        with self._lock:
            if self._memory_association_repo is None:
                self._memory_association_repo = MemoryAssociationRepository(self._orm_manager)
            return self._memory_association_repo

    # Service getters
    def get_campaign_service(self) -> "CampaignService":
        """Get or create the campaign service."""
        from task_crusade_mcp.services.campaign_service import CampaignService

        with self._lock:
            if self._campaign_service is None:
                self._campaign_service = CampaignService(
                    campaign_repo=self.get_campaign_repository(),
                    task_repo=self.get_task_repository(),
                    memory_session_repo=self.get_memory_session_repository(),
                    memory_entity_repo=self.get_memory_entity_repository(),
                    memory_association_repo=self.get_memory_association_repository(),
                )
            return self._campaign_service

    def get_task_service(self) -> "TaskService":
        """Get or create the task service."""
        from task_crusade_mcp.services.task_service import TaskService

        with self._lock:
            if self._task_service is None:
                self._task_service = TaskService(
                    task_repo=self.get_task_repository(),
                    campaign_repo=self.get_campaign_repository(),
                    memory_session_repo=self.get_memory_session_repository(),
                    memory_entity_repo=self.get_memory_entity_repository(),
                    memory_association_repo=self.get_memory_association_repository(),
                )
            return self._task_service
