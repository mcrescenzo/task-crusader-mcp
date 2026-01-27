"""TUI widget components for Task Crusade."""

from task_crusade_mcp.tui.widgets.bulk_actions_modal import BulkActionsModal
from task_crusade_mcp.tui.widgets.bulk_delete_modal import BulkDeleteModal
from task_crusade_mcp.tui.widgets.campaign_list import CampaignListWidget
from task_crusade_mcp.tui.widgets.delete_modal import DeleteModal
from task_crusade_mcp.tui.widgets.dependency_modal import DependencyModal
from task_crusade_mcp.tui.widgets.help_modal import HelpModal
from task_crusade_mcp.tui.widgets.new_campaign_modal import NewCampaignModal
from task_crusade_mcp.tui.widgets.new_task_modal import NewTaskModal
from task_crusade_mcp.tui.widgets.task_data_table import TaskDataTable
from task_crusade_mcp.tui.widgets.task_detail import TaskDetailWidget

__all__ = [
    "CampaignListWidget",
    "TaskDataTable",
    "TaskDetailWidget",
    "DeleteModal",
    "BulkActionsModal",
    "BulkDeleteModal",
    "NewTaskModal",
    "NewCampaignModal",
    "HelpModal",
    "DependencyModal",
]
