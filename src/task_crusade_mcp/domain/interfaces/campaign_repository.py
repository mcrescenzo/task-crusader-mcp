"""Campaign Repository Interface."""

from typing import Any, Dict, List, Optional, Protocol

from task_crusade_mcp.domain.entities.campaign import CampaignDTO
from task_crusade_mcp.domain.entities.result_types import DomainResult


class ICampaignRepository(Protocol):
    """Protocol for campaign repository operations."""

    def create_campaign(self, campaign_data: Dict[str, Any]) -> DomainResult[CampaignDTO]:
        """Create a new campaign."""
        ...

    def get(self, campaign_id: str) -> DomainResult[CampaignDTO]:
        """Get campaign by ID."""
        ...

    def get_by_name(self, name: str) -> DomainResult[CampaignDTO]:
        """Get campaign by name."""
        ...

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[CampaignDTO]]:
        """List campaigns with optional filtering."""
        ...

    def update(self, campaign_id: str, updates: Dict[str, Any]) -> DomainResult[CampaignDTO]:
        """Update a campaign."""
        ...

    def delete(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a campaign."""
        ...

    def get_progress_summary(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """Get lightweight progress summary for a campaign."""
        ...

    def get_campaign_with_tasks(
        self, campaign_id: str, include_task_details: bool = True
    ) -> DomainResult[Dict[str, Any]]:
        """Get campaign with associated tasks."""
        ...
