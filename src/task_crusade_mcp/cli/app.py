"""CLI application using Typer."""

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError as e:
    raise ImportError(
        "CLI requires typer and rich. Install with: pip install task-crusader-mcp[cli]"
    ) from e

import json
import sys
from typing import Optional

from task_crusade_mcp.services import get_service_factory

console = Console()
app = typer.Typer(
    name="crusader",
    help="Task Crusade - Your AI coding assistant's quest companion",
    no_args_is_help=True,
)


# Campaign commands
campaign_app = typer.Typer(help="Campaign management commands")
app.add_typer(campaign_app, name="campaign")


@campaign_app.command("create")
def campaign_create(
    name: str = typer.Argument(..., help="Campaign name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority (low/medium/high)"),
) -> None:
    """Create a new campaign."""
    factory = get_service_factory()
    service = factory.get_campaign_service()
    result = service.create_campaign(name=name, description=description, priority=priority)

    if result.is_success:
        console.print(f"[green]Campaign created:[/green] {result.data['id']}")
        console.print(f"Name: {result.data['name']}")
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


@campaign_app.command("list")
def campaign_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List all campaigns."""
    factory = get_service_factory()
    service = factory.get_campaign_service()
    result = service.list_campaigns(status=status)

    if result.is_success:
        campaigns = result.data or []
        if not campaigns:
            console.print("No campaigns found.")
            return

        table = Table(title="Campaigns")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Status")
        table.add_column("Priority")
        table.add_column("Tasks")

        for c in campaigns:
            stats = c.get("task_statistics", {})
            total = stats.get("total", 0)
            done = stats.get("by_status", {}).get("done", 0)
            table.add_row(
                c["id"][:8] + "...",
                c["name"],
                c["status"],
                c["priority"],
                f"{done}/{total}",
            )

        console.print(table)
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


@campaign_app.command("show")
def campaign_show(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
) -> None:
    """Show campaign details."""
    factory = get_service_factory()
    service = factory.get_campaign_service()
    result = service.get_campaign_with_tasks(campaign_id)

    if result.is_success:
        data = result.data
        console.print(f"\n[bold]{data['name']}[/bold]")
        console.print(f"ID: {data['id']}")
        console.print(f"Status: {data['status']}")
        console.print(f"Priority: {data['priority']}")
        if data.get("description"):
            console.print(f"Description: {data['description']}")

        tasks = data.get("tasks", [])
        if tasks:
            console.print(f"\n[bold]Tasks ({len(tasks)}):[/bold]")
            for t in tasks:
                status_icon = {"done": "[green]✓", "in-progress": "[yellow]→", "pending": "○"}.get(
                    t["status"], "○"
                )
                console.print(f"  {status_icon}[/] {t['title']} ({t['status']})")
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


# Campaign subcommand groups
next_actionable_app = typer.Typer(help="Get next actionable task")
campaign_app.add_typer(next_actionable_app, name="next-actionable")

progress_app = typer.Typer(help="Campaign progress commands")
campaign_app.add_typer(progress_app, name="progress")


@next_actionable_app.command("task")
def campaign_next_actionable_task(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    context_depth: str = typer.Option("basic", "--context-depth", help="Context depth (basic/full)"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
) -> None:
    """Get the next actionable task for a campaign."""
    factory = get_service_factory()
    service = factory.get_campaign_service()
    result = service.get_next_actionable_task(campaign_id, context_depth=context_depth)

    if result.is_success:
        if format == "json":
            json.dump({"success": True, "data": result.data}, sys.stdout, default=str)
            sys.stdout.write("\n")
        else:
            data = result.data
            task = data.get("task") if isinstance(data, dict) else None
            if task:
                console.print(f"\n[bold]Next Task:[/bold] {task.get('title', 'N/A')}")
                console.print(f"ID: {task.get('id', 'N/A')}")
                console.print(f"Priority: {task.get('priority', 'N/A')}")
            else:
                console.print("No actionable tasks available.")
    else:
        if format == "json":
            json.dump({"success": False, "error": result.error_message}, sys.stdout, default=str)
            sys.stdout.write("\n")
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


@progress_app.command("summary")
def campaign_progress_summary(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
) -> None:
    """Get campaign progress summary."""
    factory = get_service_factory()
    service = factory.get_campaign_service()
    result = service.get_progress_summary(campaign_id)

    if result.is_success:
        if format == "json":
            json.dump({"success": True, "data": result.data}, sys.stdout, default=str)
            sys.stdout.write("\n")
        else:
            data = result.data
            console.print(f"\n[bold]Campaign Progress[/bold]")
            console.print(f"Campaign: {data.get('campaign_name', 'N/A')}")
            console.print(f"Total Tasks: {data.get('total_tasks', 0)}")
            tasks_by_status = data.get("tasks_by_status", {})
            console.print(f"Done: {tasks_by_status.get('done', 0)}")
            console.print(f"In Progress: {tasks_by_status.get('in-progress', 0)}")
            console.print(f"Pending: {tasks_by_status.get('pending', 0)}")
            console.print(f"Completion: {data.get('completion_rate', 0):.0f}%")
    else:
        if format == "json":
            json.dump({"success": False, "error": result.error_message}, sys.stdout, default=str)
            sys.stdout.write("\n")
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


# Task commands
task_app = typer.Typer(help="Task management commands")
app.add_typer(task_app, name="task")


@task_app.command("create")
def task_create(
    title: str = typer.Argument(..., help="Task title"),
    campaign_id: str = typer.Option(..., "--campaign", "-c", help="Campaign ID"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority"),
) -> None:
    """Create a new task."""
    factory = get_service_factory()
    service = factory.get_task_service()
    result = service.create_task(
        title=title,
        campaign_id=campaign_id,
        description=description,
        priority=priority,
    )

    if result.is_success:
        console.print(f"[green]Task created:[/green] {result.data['id']}")
        console.print(f"Title: {result.data['title']}")
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


@task_app.command("show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """Show task details."""
    factory = get_service_factory()
    service = factory.get_task_service()
    result = service.get_task(task_id)

    if result.is_success:
        data = result.data
        console.print(f"\n[bold]{data['title']}[/bold]")
        console.print(f"ID: {data['id']}")
        console.print(f"Status: {data['status']}")
        console.print(f"Priority: {data['priority']}")

        criteria = data.get("acceptance_criteria_details", [])
        if criteria:
            console.print(f"\n[bold]Acceptance Criteria ({len(criteria)}):[/bold]")
            for c in criteria:
                icon = "[green]✓" if c["is_met"] else "○"
                console.print(f"  {icon}[/] {c['content']}")
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


@task_app.command("update")
def task_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
) -> None:
    """Update a task."""
    factory = get_service_factory()
    service = factory.get_task_service()

    updates = {}
    if status:
        updates["status"] = status
    if priority:
        updates["priority"] = priority

    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    result = service.update_task(task_id, **updates)

    if result.is_success:
        console.print(f"[green]Task updated:[/green] {result.data['title']}")
    else:
        console.print(f"[red]Error:[/red] {result.error_message}")
        raise typer.Exit(1)


def create_app() -> typer.Typer:
    """Create and return the Typer app."""
    return app
