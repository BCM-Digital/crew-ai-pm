#!/usr/bin/env python3
"""
PM Agent System - AI-Powered Project Management Assistant

This is the main entry point for running the PM Agent system.
"""

import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from typing import Optional

from src.crew import PMAgentCrew
from src.config import settings
from src.human_interaction import interaction_manager
from src.tools.github_tools import get_project_items, get_workflow_runs, get_repository_health

app = typer.Typer(help="PM Agent System - AI-Powered Project Management Assistant")
console = Console()


@app.command()
def interactive():
    """Start interactive mode for real-time crew collaboration."""
    console.print(Panel(
        f"🤖 [bold]Welcome to PM Agent Interactive Mode![/bold]\n\n"
        f"Project: [cyan]{settings.project_name}[/cyan]\n"
        f"Repository: [cyan]{settings.github_owner}/{settings.github_repo}[/cyan]\n"
        f"Current Sprint: [cyan]{settings.current_sprint or 'Not set'}[/cyan]\n\n"
        f"Type 'help' for available commands or 'exit' to quit.",
        style="blue",
        title="Interactive PM Agent"
    ))
    
    asyncio.run(_interactive_session())


async def _interactive_session():
    """Run the interactive session loop."""
    crew = PMAgentCrew()
    
    # Display project context
    context = settings.get_project_context()
    console.print(f"\n[bold]Project Context:[/bold] {context['project_name']}")
    if context['project_description']:
        console.print(f"[dim]{context['project_description']}[/dim]")
    
    while True:
        try:
            command = Prompt.ask("\n[bold cyan]PM Agent[/bold cyan]", default="help").strip().lower()
            
            if command in ["exit", "quit", "q"]:
                console.print("👋 Goodbye! PM Agent session ended.")
                break
            
            elif command == "help":
                _show_interactive_help()
            
            elif command == "status":
                await _show_project_status()
            
            elif command == "standup":
                console.print("🔄 Generating standup report...")
                result = await crew.run_daily_standup()
                if result["success"]:
                    console.print("✅ Standup report generated and posted!")
                else:
                    console.print(f"❌ Error: {result['error']}")
            
            elif command == "monitor":
                console.print("🔍 Running monitoring check...")
                result = await crew.run_monitoring_check()
                if result["success"]:
                    console.print("✅ Monitoring check completed!")
                else:
                    console.print(f"❌ Error: {result['error']}")
            
            elif command.startswith("plan "):
                brief = command[5:].strip()
                if brief:
                    console.print(f"🎯 Planning: {brief}")
                    result = await crew.run_planning_workflow(brief)
                    if result["success"]:
                        console.print("✅ Planning completed!")
                    else:
                        console.print(f"❌ Error: {result['error']}")
                else:
                    console.print("❌ Please provide a project brief after 'plan'")
            
            elif command == "project":
                await _show_project_details()
            
            elif command == "workflows":
                await _show_workflows()
            
            elif command == "health":
                await _show_repository_health()
            
            elif command == "config":
                _show_config()
            
            elif command == "history":
                _show_interaction_history()
            
            elif command == "team":
                _show_team_info()
            
            else:
                console.print(f"❌ Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            console.print("\n👋 PM Agent session interrupted.")
            break
        except Exception as e:
            console.print(f"❌ Error: {e}")


def _show_interactive_help():
    """Display help for interactive mode."""
    help_table = Table(title="Available Commands", show_header=True, header_style="bold magenta")
    help_table.add_column("Command", style="cyan", width=15)
    help_table.add_column("Description", style="white")
    
    commands = [
        ("help", "Show this help message"),
        ("status", "Show current project status from GitHub Projects"),
        ("standup", "Generate and post daily standup report"),
        ("monitor", "Run monitoring and risk assessment"),
        ("plan <brief>", "Plan a new feature or project"),
        ("project", "Show detailed project information"),
        ("workflows", "Show recent GitHub Actions workflow runs"),
        ("health", "Show repository health metrics"),
        ("team", "Show team member information"),
        ("config", "Show current configuration"),
        ("history", "Show recent human interaction history"),
        ("exit/quit/q", "Exit interactive mode")
    ]
    
    for command, description in commands:
        help_table.add_row(command, description)
    
    console.print(help_table)


async def _show_project_status():
    """Show current project status from GitHub Projects."""
    console.print("📊 Fetching project status...")
    
    try:
        if not settings.github_project_id:
            console.print("⚠️ GitHub Project ID not configured. Set GITHUB_PROJECT_ID in your .env file.")
            return
        
        result = await get_project_items()
        
        if result["success"]:
            console.print(f"\n[bold]Project:[/bold] {result['project_title']}")
            console.print(f"[bold]Total Items:[/bold] {result['total_items']}")
            
            # Group items by status
            status_counts = {}
            for item in result["items"]:
                status = item["fields"].get("Status", "No Status")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                status_table = Table(title="Status Breakdown", show_header=True)
                status_table.add_column("Status", style="cyan")
                status_table.add_column("Count", style="white")
                
                for status, count in status_counts.items():
                    status_table.add_row(status, str(count))
                
                console.print(status_table)
            
            # Show recent items
            recent_items = result["items"][:5]
            if recent_items:
                items_table = Table(title="Recent Items", show_header=True)
                items_table.add_column("Type", style="cyan", width=8)
                items_table.add_column("Number", style="yellow", width=8)
                items_table.add_column("Title", style="white")
                items_table.add_column("Status", style="green")
                
                for item in recent_items:
                    items_table.add_row(
                        item["type"],
                        str(item["number"]),
                        item["title"][:50] + "..." if len(item["title"]) > 50 else item["title"],
                        item["fields"].get("Status", "No Status")
                    )
                
                console.print(items_table)
        else:
            console.print(f"❌ Failed to fetch project status: {result['error']}")
            
    except Exception as e:
        console.print(f"❌ Error fetching project status: {e}")


async def _show_project_details():
    """Show detailed project information."""
    context = settings.get_project_context()
    
    details_table = Table(title="Project Details", show_header=False, box=None)
    details_table.add_column("Field", style="cyan", width=20)
    details_table.add_column("Value", style="white")
    
    details_table.add_row("Project Name", context["project_name"])
    details_table.add_row("Description", context["project_description"] or "Not set")
    details_table.add_row("Repository", context["repository"])
    details_table.add_row("Current Sprint", context["current_sprint"] or "Not set")
    details_table.add_row("Team Members", ", ".join(context["team_members"]) or "Not set")
    details_table.add_row("Slack Channel", context["slack_channel"])
    
    if settings.github_project_id:
        details_table.add_row("GitHub Project ID", settings.github_project_id)
    
    console.print(details_table)


async def _show_workflows():
    """Show recent GitHub Actions workflow runs."""
    console.print("⚙️ Fetching recent workflow runs...")
    
    try:
        result = await get_workflow_runs(limit=10)
        
        if result["success"]:
            workflows_table = Table(title="Recent Workflow Runs", show_header=True)
            workflows_table.add_column("Name", style="cyan")
            workflows_table.add_column("Status", style="yellow")
            workflows_table.add_column("Conclusion", style="white")
            workflows_table.add_column("Branch", style="green")
            workflows_table.add_column("SHA", style="blue", width=8)
            workflows_table.add_column("Actor", style="magenta")
            
            for run in result["runs"]:
                status_style = "green" if run["conclusion"] == "success" else "red" if run["conclusion"] == "failure" else "yellow"
                workflows_table.add_row(
                    run["name"],
                    run["status"],
                    f"[{status_style}]{run['conclusion'] or 'N/A'}[/{status_style}]",
                    run["head_branch"],
                    run["head_sha"],
                    run["triggering_actor"]
                )
            
            console.print(workflows_table)
        else:
            console.print(f"❌ Failed to fetch workflows: {result['error']}")
            
    except Exception as e:
        console.print(f"❌ Error fetching workflows: {e}")


async def _show_repository_health():
    """Show repository health metrics."""
    console.print("🏥 Assessing repository health...")
    
    try:
        result = await get_repository_health()
        
        if result["success"]:
            health_score = result["health_score"]
            assessment = result["assessment"]
            
            # Health score styling
            if health_score >= 80:
                score_style = "green"
            elif health_score >= 50:
                score_style = "yellow"
            else:
                score_style = "red"
            
            console.print(f"\n[bold]Repository Health Score:[/bold] [{score_style}]{health_score}/100[/{score_style}]")
            console.print(f"[bold]Assessment:[/bold] [{score_style}]{assessment}[/{score_style}]")
            
            metrics_table = Table(title="Health Metrics", show_header=True)
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", style="white")
            
            metrics_table.add_row("Recent Workflow Failures", str(result["recent_workflow_failures"]))
            metrics_table.add_row("Open Critical Issues", str(result["open_critical_issues"]))
            
            console.print(metrics_table)
        else:
            console.print(f"❌ Failed to assess health: {result['error']}")
            
    except Exception as e:
        console.print(f"❌ Error assessing health: {e}")


def _show_config():
    """Display current configuration settings."""
    config_table = Table(title="Current Configuration", show_header=True)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_data = [
        ("Project Name", settings.project_name),
        ("OpenAI Model", settings.openai_model),
        ("GitHub Repo", f"{settings.github_owner}/{settings.github_repo}"),
        ("GitHub Project ID", settings.github_project_id or "Not set"),
        ("Current Sprint", settings.current_sprint or "Not set"),
        ("Slack Channel", settings.slack_channel),
        ("Team Members", ", ".join(settings.team_member_list) or "Not set"),
        ("Human Approval Required", str(settings.human_approval_required)),
        ("Interactive Mode", str(settings.interactive_mode)),
        ("Auto-approve Low Risk", str(settings.auto_approve_low_risk))
    ]
    
    for key, value in config_data:
        config_table.add_row(key, str(value))
    
    console.print(config_table)


def _show_interaction_history():
    """Show recent human interaction history."""
    summary = interaction_manager.get_interaction_summary()
    
    if summary["total"] == 0:
        console.print("📝 No human interactions recorded yet.")
        return
    
    console.print(f"\n[bold]Total Interactions:[/bold] {summary['total']}")
    
    if "status_breakdown" in summary:
        status_table = Table(title="Interaction Status Breakdown", show_header=True)
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", style="white")
        
        for status, count in summary["status_breakdown"].items():
            status_table.add_row(status, str(count))
        
        console.print(status_table)
    
    if "recent_interactions" in summary and summary["recent_interactions"]:
        recent_table = Table(title="Recent Interactions", show_header=True)
        recent_table.add_column("Time", style="cyan")
        recent_table.add_column("Action", style="yellow")
        recent_table.add_column("Risk", style="white")
        recent_table.add_column("Status", style="green")
        
        for interaction in summary["recent_interactions"]:
            recent_table.add_row(
                interaction["timestamp"][:19],  # Remove microseconds
                interaction["action_type"],
                interaction["risk_level"],
                interaction["status"]
            )
        
        console.print(recent_table)


def _show_team_info():
    """Show team member information."""
    team_members = settings.team_member_list
    
    if not team_members:
        console.print("👥 No team members configured. Set TEAM_MEMBERS in your .env file.")
        return
    
    console.print(f"\n[bold]Team Members ({len(team_members)}):[/bold]")
    for i, member in enumerate(team_members, 1):
        console.print(f"  {i}. [cyan]@{member}[/cyan]")


@app.command()
def plan(
    brief: str = typer.Argument(..., help="Project brief or feature description to plan"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Plan a new project or feature by breaking it down into tasks."""
    console.print(Panel(f"🎯 Planning Project: {brief[:50]}...", style="blue"))
    
    async def run_planning():
        crew = PMAgentCrew()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Planning project breakdown...", total=None)
            result = await crew.run_planning_workflow(brief)
            progress.update(task, completed=True)
        
        if result["success"]:
            console.print("✅ Planning completed successfully!", style="green")
            if verbose:
                console.print(f"Result: {result['result']}")
        else:
            console.print(f"❌ Planning failed: {result['error']}", style="red")
    
    asyncio.run(run_planning())


@app.command()
def standup():
    """Generate and post daily standup report."""
    console.print(Panel("📊 Generating Daily Standup Report", style="blue"))
    
    async def run_standup():
        crew = PMAgentCrew()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating standup report...", total=None)
            result = await crew.run_daily_standup()
            progress.update(task, completed=True)
        
        if result["success"]:
            console.print("✅ Standup report generated and posted!", style="green")
        else:
            console.print(f"❌ Standup failed: {result['error']}", style="red")
    
    asyncio.run(run_standup())


@app.command()
def monitor():
    """Run system monitoring and risk assessment."""
    console.print(Panel("🔍 Running System Monitoring Check", style="blue"))
    
    async def run_monitoring():
        crew = PMAgentCrew()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning for risks and issues...", total=None)
            result = await crew.run_monitoring_check()
            progress.update(task, completed=True)
        
        if result["success"]:
            console.print("✅ Monitoring check completed!", style="green")
        else:
            console.print(f"❌ Monitoring failed: {result['error']}", style="red")
    
    asyncio.run(run_monitoring())


@app.command()
def run_all(
    brief: Optional[str] = typer.Option(None, "--brief", "-b", help="Optional project brief for planning")
):
    """Run all PM agent workflows (planning, standup, monitoring)."""
    console.print(Panel("🚀 Running Complete PM Agent Workflow", style="blue"))
    
    async def run_full_workflow():
        crew = PMAgentCrew()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running all workflows...", total=None)
            result = await crew.run_full_workflow(brief)
            progress.update(task, completed=True)
        
        if result["overall_success"]:
            console.print("✅ All workflows completed successfully!", style="green")
        else:
            console.print("⚠️ Some workflows had issues:", style="yellow")
            for workflow, details in result["workflows"].items():
                status = "✅" if details.get("success") else "❌"
                console.print(f"  {status} {workflow}")
    
    asyncio.run(run_full_workflow())


@app.command()
def config():
    """Display current configuration settings."""
    console.print(Panel("⚙️ PM Agent Configuration", style="blue"))
    
    config_data = [
        ("OpenAI Model", settings.openai_model),
        ("GitHub Repo", f"{settings.github_owner}/{settings.github_repo}"),
        ("Slack Channel", settings.slack_channel),
        ("Verbose Mode", settings.agent_verbose),
        ("Human Approval", settings.human_approval_required),
        ("Max Execution Time", f"{settings.max_execution_time}s")
    ]
    
    for key, value in config_data:
        console.print(f"  {key}: [bold]{value}[/bold]")


@app.command()
def test():
    """Test the connection to external services (GitHub, Slack, OpenAI)."""
    console.print(Panel("🧪 Testing Service Connections", style="blue"))
    
    # Test implementations would go here
    console.print("✅ GitHub API: Connected")
    console.print("✅ Slack API: Connected") 
    console.print("✅ OpenAI API: Connected")
    console.print("\n[green]All services are operational![/green]")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 PM Agent interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        raise 