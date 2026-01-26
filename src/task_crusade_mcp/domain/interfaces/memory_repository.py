"""Memory Repository Interfaces.

These interfaces define contracts for memory operations used internally
by task services. Memory is NOT exposed via MCP but is essential for
storing task acceptance criteria, research items, implementation notes,
and testing steps.
"""

from typing import Any, Dict, List, Optional, Protocol

from task_crusade_mcp.domain.entities.memory import (
    MemoryEntityDTO,
    MemorySessionDTO,
    MemoryTaskAssociationDTO,
)
from task_crusade_mcp.domain.entities.result_types import DomainResult


class IMemorySessionRepository(Protocol):
    """Protocol for memory session repository operations."""

    def create(self, session_data: Dict[str, Any]) -> DomainResult[MemorySessionDTO]:
        """Create a new memory session."""
        ...

    def get(self, session_id: str) -> DomainResult[MemorySessionDTO]:
        """Get memory session by ID."""
        ...

    def get_by_name(self, name: str) -> DomainResult[MemorySessionDTO]:
        """Get memory session by name."""
        ...

    def get_or_create(
        self, name: str, workflow_type: Optional[str] = None
    ) -> DomainResult[MemorySessionDTO]:
        """Get existing session by name or create a new one."""
        ...

    def list(
        self,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[MemorySessionDTO]]:
        """List memory sessions with optional filtering."""
        ...

    def update(self, session_id: str, updates: Dict[str, Any]) -> DomainResult[MemorySessionDTO]:
        """Update a memory session."""
        ...

    def delete(self, session_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory session."""
        ...


class IMemoryEntityRepository(Protocol):
    """Protocol for memory entity repository operations."""

    def create(self, entity_data: Dict[str, Any]) -> DomainResult[MemoryEntityDTO]:
        """Create a new memory entity."""
        ...

    def get(self, entity_id: str) -> DomainResult[MemoryEntityDTO]:
        """Get memory entity by ID."""
        ...

    def get_by_session_and_name(self, session_id: str, name: str) -> DomainResult[MemoryEntityDTO]:
        """Get memory entity by session and name."""
        ...

    def list_by_session(
        self,
        session_id: str,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[MemoryEntityDTO]]:
        """List memory entities for a session with optional type filter."""
        ...

    def update(self, entity_id: str, updates: Dict[str, Any]) -> DomainResult[MemoryEntityDTO]:
        """Update a memory entity."""
        ...

    def delete(self, entity_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory entity."""
        ...

    def add_observation(self, entity_id: str, observation: str) -> DomainResult[MemoryEntityDTO]:
        """Add an observation to a memory entity."""
        ...


class IMemoryAssociationRepository(Protocol):
    """Protocol for memory task association repository operations."""

    def create(self, association_data: Dict[str, Any]) -> DomainResult[MemoryTaskAssociationDTO]:
        """Create a new memory task association."""
        ...

    def get(self, association_id: str) -> DomainResult[MemoryTaskAssociationDTO]:
        """Get memory task association by ID."""
        ...

    def list_by_task(
        self,
        task_id: str,
        association_type: Optional[str] = None,
    ) -> DomainResult[List[MemoryTaskAssociationDTO]]:
        """List associations for a task with optional type filter."""
        ...

    def list_by_campaign(
        self,
        campaign_id: str,
        association_type: Optional[str] = None,
    ) -> DomainResult[List[MemoryTaskAssociationDTO]]:
        """List associations for a campaign with optional type filter."""
        ...

    def update(
        self, association_id: str, updates: Dict[str, Any]
    ) -> DomainResult[MemoryTaskAssociationDTO]:
        """Update a memory task association."""
        ...

    def delete(self, association_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory task association."""
        ...

    def reorder(
        self, association_id: str, new_order: int
    ) -> DomainResult[MemoryTaskAssociationDTO]:
        """Update the order position of an association."""
        ...
