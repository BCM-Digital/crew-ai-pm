"""Human-in-the-loop interaction system for PM Agent crew."""

import asyncio
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown

from .config import settings

console = Console()


class ApprovalStatus(Enum):
    """Status of human approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"


class RiskLevel(Enum):
    """Risk levels for agent actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HumanApprovalRequest:
    """Represents a request for human approval."""
    
    def __init__(
        self,
        action_type: str,
        description: str,
        proposed_action: Dict[str, Any],
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ):
        self.id = str(uuid4())
        self.action_type = action_type
        self.description = description
        self.proposed_action = proposed_action
        self.risk_level = risk_level
        self.context = context or {}
        self.timeout = timeout or settings.approval_timeout
        self.created_at = datetime.now()
        self.status = ApprovalStatus.PENDING
        self.response = None
        self.modified_action = None
        # Future to coordinate web-driven responses
        try:
            loop = asyncio.get_event_loop()
            self._future: asyncio.Future = loop.create_future()
        except RuntimeError:
            # Fallback: will be set later if loop not available
            self._future = None
 
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "description": self.description,
            "proposed_action": self.proposed_action,
            "risk_level": self.risk_level.value,
            "context": self.context,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value
        }


class HumanInteractionManager:
    """Manages human-in-the-loop interactions."""
    
    def __init__(self):
        self.pending_requests: List[HumanApprovalRequest] = []
        self._pending_by_id: Dict[str, HumanApprovalRequest] = {}
        self.interaction_history: List[Dict[str, Any]] = []
    
    async def request_approval(
        self,
        action_type: str,
        description: str,
        proposed_action: Dict[str, Any],
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request human approval for an agent action.
        
        Args:
            action_type: Type of action (e.g., "create_issue", "merge_pr")
            description: Human-readable description of the action
            proposed_action: The action parameters to be executed
            risk_level: Risk level of the action
            context: Additional context for decision making
        
        Returns:
            Dictionary with approval status and potentially modified action
        """
        # Auto-approve low-risk actions if configured
        if (risk_level == RiskLevel.LOW and 
            settings.auto_approve_low_risk and 
            not settings.human_approval_required):
            return {
                "status": ApprovalStatus.APPROVED.value,
                "action": proposed_action,
                "message": "Auto-approved (low risk)"
            }
        
        # Skip approval if not required for non-critical actions
        if (not settings.human_approval_required and 
            risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]):
            return {
                "status": ApprovalStatus.APPROVED.value,
                "action": proposed_action,
                "message": "Auto-approved (approval not required)"
            }
        
        # Create approval request
        request = HumanApprovalRequest(
            action_type=action_type,
            description=description,
            proposed_action=proposed_action,
            risk_level=risk_level,
            context=context
        )
        
        self.pending_requests.append(request)
        self._pending_by_id[request.id] = request
 
        if settings.web_interface_enabled:
            # In web mode, wait for external resolution via API
            # Ensure future exists
            if request._future is None:
                request._future = asyncio.get_event_loop().create_future()
            try:
                response = await asyncio.wait_for(request._future, timeout=request.timeout)
            except asyncio.TimeoutError:
                response = {
                    "status": ApprovalStatus.TIMEOUT.value,
                    "action": None,
                    "message": "Request timed out"
                }
        else:
            # Console interaction path
            await self._display_approval_request(request)
            response = await self._get_user_response(request)
        
        # Record interaction
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "risk_level": risk_level.value,
            "status": response["status"],
            "description": description
        })
        
        # Remove from pending
        if request in self.pending_requests:
            self.pending_requests.remove(request)
        if request.id in self._pending_by_id:
            del self._pending_by_id[request.id]
        
        return response
    
    def list_pending(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.pending_requests]
 
    def resolve_request(self, request_id: str, decision: str, modified_action: Optional[Dict[str, Any]] = None, message: str = "") -> Dict[str, Any]:
        req = self._pending_by_id.get(request_id)
        if not req:
            return {"error": "not_found"}
        if decision == ApprovalStatus.APPROVED.value:
            response = {"status": ApprovalStatus.APPROVED.value, "action": req.proposed_action, "message": message or "Approved via web"}
        elif decision == ApprovalStatus.REJECTED.value:
            response = {"status": ApprovalStatus.REJECTED.value, "action": None, "message": message or "Rejected via web"}
        elif decision == ApprovalStatus.MODIFIED.value:
            response = {"status": ApprovalStatus.MODIFIED.value, "action": modified_action or req.proposed_action, "message": message or "Modified via web"}
        else:
            return {"error": "invalid_decision"}
        req.status = ApprovalStatus(response["status"])  # type: ignore[arg-type]
        req.response = response
        if req._future and not req._future.done():
            req._future.set_result(response)
        return {"ok": True}
 
    async def _display_approval_request(self, request: HumanApprovalRequest):
        """Display approval request to the user."""
        console.print("\n" + "="*60)
        
        # Risk level styling
        risk_colors = {
            RiskLevel.LOW: "green",
            RiskLevel.MEDIUM: "yellow", 
            RiskLevel.HIGH: "orange",
            RiskLevel.CRITICAL: "red"
        }
        
        color = risk_colors.get(request.risk_level, "white")
        
        console.print(Panel(
            f"🤝 [bold]Human Approval Required[/bold]\n\n"
            f"[bold]Action:[/bold] {request.action_type}\n"
            f"[bold]Risk Level:[/bold] [{color}]{request.risk_level.value.upper()}[/{color}]\n"
            f"[bold]Description:[/bold] {request.description}",
            style=color,
            title="Agent Requesting Permission"
        ))
        
        # Show proposed action details
        if request.proposed_action:
            console.print("\n[bold]Proposed Action Details:[/bold]")
            table = Table(show_header=False, box=None)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in request.proposed_action.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                table.add_row(str(key), str(value))
            
            console.print(table)
        
        # Show context if available
        if request.context:
            console.print(f"\n[bold]Context:[/bold]")
            for key, value in request.context.items():
                console.print(f"  {key}: {value}")

    async def _get_user_response(self, request: HumanApprovalRequest) -> Dict[str, Any]:
        """Get user response to approval request."""
        try:
            # Check for timeout
            timeout_time = request.created_at + timedelta(seconds=request.timeout)
            if datetime.now() > timeout_time:
                return {
                    "status": ApprovalStatus.TIMEOUT.value,
                    "action": None,
                    "message": "Request timed out"
                }
            
            console.print("\n[bold]Options:[/bold]")
            console.print("  [green]a[/green] - Approve action as proposed")
            console.print("  [red]r[/red] - Reject action")
            console.print("  [yellow]m[/yellow] - Modify action parameters")
            console.print("  [blue]i[/blue] - Get more information")
            console.print("  [gray]s[/gray] - Skip (auto-approve for this session)")
            
            while True:
                choice = Prompt.ask(
                    "\nWhat would you like to do?",
                    choices=["a", "r", "m", "i", "s"],
                    default="a"
                ).lower()
                
                if choice == "a":
                    return {
                        "status": ApprovalStatus.APPROVED.value,
                        "action": request.proposed_action,
                        "message": "Approved by user"
                    }
                
                elif choice == "r":
                    reason = Prompt.ask("Reason for rejection (optional)", default="")
                    return {
                        "status": ApprovalStatus.REJECTED.value,
                        "action": None,
                        "message": f"Rejected by user: {reason}"
                    }
                
                elif choice == "m":
                    modified_action = await self._modify_action(request.proposed_action)
                    if modified_action:
                        return {
                            "status": ApprovalStatus.MODIFIED.value,
                            "action": modified_action,
                            "message": "Modified by user"
                        }
                    continue
                
                elif choice == "i":
                    await self._show_additional_info(request)
                    continue
                
                elif choice == "s":
                    # Temporarily disable approval for this session
                    console.print("[yellow]Auto-approving remaining actions for this session...[/yellow]")
                    settings.human_approval_required = False
                    return {
                        "status": ApprovalStatus.APPROVED.value,
                        "action": request.proposed_action,
                        "message": "Auto-approved (user skipped)"
                    }
        
        except KeyboardInterrupt:
            return {
                "status": ApprovalStatus.REJECTED.value,
                "action": None,
                "message": "Interrupted by user"
            }

    async def _modify_action(self, original_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Allow user to modify action parameters."""
        console.print("\n[bold]Modify Action Parameters:[/bold]")
        console.print("Current parameters:")
        
        # Display current parameters
        for key, value in original_action.items():
            console.print(f"  {key}: {value}")
        
        modified = original_action.copy()
        
        while True:
            console.print("\nOptions:")
            console.print("  [cyan]<key>=<value>[/cyan] - Set parameter")
            console.print("  [green]done[/green] - Finish modifications")
            console.print("  [red]cancel[/red] - Cancel modifications")
            
            input_str = Prompt.ask("Enter modification").strip()
            
            if input_str.lower() == "done":
                return modified
            elif input_str.lower() == "cancel":
                return None
            elif "=" in input_str:
                try:
                    key, value = input_str.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Try to parse value as JSON, fallback to string
                    try:
                        value = json.loads(value)
                    except:
                        pass
                    
                    modified[key] = value
                    console.print(f"Set {key} = {value}")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            else:
                console.print("[red]Invalid format. Use key=value[/red]")
    
    async def _show_additional_info(self, request: HumanApprovalRequest):
        """Show additional information about the request."""
        console.print("\n[bold]Additional Information:[/bold]")
        
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Field", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Request Created", request.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        info_table.add_row("Timeout", f"{request.timeout} seconds")
        info_table.add_row("Project", f"{settings.github_owner}/{settings.github_repo}")
        
        if settings.current_sprint:
            info_table.add_row("Current Sprint", settings.current_sprint)
        
        console.print(info_table)
        
        if request.context:
            console.print("\n[bold]Context Details:[/bold]")
            console.print(json.dumps(request.context, indent=2))
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """Get summary of human interactions."""
        total_interactions = len(self.interaction_history)
        if total_interactions == 0:
            return {"total": 0, "summary": "No interactions yet"}
        
        status_counts = {}
        risk_counts = {}
        
        for interaction in self.interaction_history:
            status = interaction["status"]
            risk = interaction["risk_level"]
            
            status_counts[status] = status_counts.get(status, 0) + 1
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        return {
            "total": total_interactions,
            "status_breakdown": status_counts,
            "risk_breakdown": risk_counts,
            "recent_interactions": self.interaction_history[-5:]  # Last 5
        }


# Global interaction manager instance
interaction_manager = HumanInteractionManager()


# Convenience functions for agents to use
async def request_approval(
    action_type: str,
    description: str,
    proposed_action: Dict[str, Any],
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Request human approval for an action."""
    return await interaction_manager.request_approval(
        action_type, description, proposed_action, risk_level, context
    )


async def request_approval_for_github_action(
    action_name: str,
    action_params: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Request approval specifically for GitHub actions."""
    risk_level = RiskLevel.LOW
    
    # Determine risk level based on action
    if action_name in ["delete_issue", "close_issue", "merge_pull_request"]:
        risk_level = RiskLevel.MEDIUM
    elif action_name in ["trigger_workflow", "update_project_item_status"]:
        risk_level = RiskLevel.HIGH
    elif "critical" in str(action_params).lower():
        risk_level = RiskLevel.CRITICAL
    
    return await request_approval(
        action_type=f"github_{action_name}",
        description=f"Execute GitHub action: {action_name}",
        proposed_action=action_params,
        risk_level=risk_level,
        context=context
    ) 