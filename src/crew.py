"""PM Agent Crew - Orchestrates multiple agents for project management tasks."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .agents.planner_agent import create_planner_agent
from .agents.reporter_agent import create_reporter_agent
from .agents.monitor_agent import create_monitor_agent
from .config import settings
from .human_interaction import request_approval, RiskLevel


class PMAgentCrew:
    """Orchestrates PM agents working together."""
    
    def __init__(self):
        """Initialize the PM Agent crew with all agents and project context."""
        # Get project context for all agents
        self.project_context = settings.get_project_context()
        
        # Initialize agents
        self.planner = create_planner_agent()
        self.reporter = create_reporter_agent()
        self.monitor = create_monitor_agent()
        
        print(f"🤖 PM Agent Crew initialized for project: {self.project_context['project_name']}")
        print(f"📁 Repository: {self.project_context['repository']}")
        if self.project_context['current_sprint']:
            print(f"🏃 Current Sprint: {self.project_context['current_sprint']}")
        if self.project_context['team_members']:
            print(f"👥 Team: {', '.join(self.project_context['team_members'])}")
    
    async def run_planning_workflow(self, project_brief: str) -> Dict[str, Any]:
        """
        Run the planning workflow for a new project or feature.
        
        Args:
            project_brief: Description of the project or feature to plan
            
        Returns:
            Dictionary with planning results
        """
        try:
            print("🎯 Starting planning workflow...")
            
            # Request human approval for planning action
            approval_result = await request_approval(
                action_type="project_planning",
                description=f"Plan and break down project: {project_brief[:100]}...",
                proposed_action={
                    "project_brief": project_brief,
                    "target_repository": self.project_context['repository'],
                    "team_members": self.project_context['team_members']
                },
                risk_level=RiskLevel.LOW,
                context=self.project_context
            )
            
            if approval_result["status"] != "approved":
                return {
                    "success": False,
                    "error": f"Planning rejected: {approval_result['message']}",
                    "details": "Human approval required for planning was not granted"
                }
            
            # Use approved (potentially modified) action
            approved_brief = approval_result["action"].get("project_brief", project_brief)
            
            # Execute planning with project context
            result = await self.planner.plan_project(approved_brief)
            
            print("✅ Planning workflow completed successfully")
            return {
                "success": True,
                "result": result,
                "approval_status": approval_result["status"],
                "project_context": self.project_context
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": "Exception occurred during planning workflow"
            }
    
    async def run_daily_standup(self) -> Dict[str, Any]:
        """
        Generate and post daily standup report.
        
        Returns:
            Dictionary with standup results
        """
        try:
            print("📊 Generating daily standup report...")
            
            # Request approval for standup report generation
            approval_result = await request_approval(
                action_type="daily_standup",
                description="Generate and post daily standup report to team",
                proposed_action={
                    "target_channel": self.project_context['slack_channel'],
                    "repository": self.project_context['repository'],
                    "include_github_projects": bool(settings.github_project_id)
                },
                risk_level=RiskLevel.LOW,
                context=self.project_context
            )
            
            if approval_result["status"] != "approved":
                return {
                    "success": False,
                    "error": f"Standup rejected: {approval_result['message']}"
                }
            
            # Execute standup generation with project context
            result = await self.reporter.generate_daily_standup()
            
            print("✅ Daily standup completed successfully")
            return {
                "success": True,
                "result": result,
                "project_context": self.project_context
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_monitoring_check(self) -> Dict[str, Any]:
        """
        Run system monitoring and risk assessment.
        
        Returns:
            Dictionary with monitoring results
        """
        try:
            print("🔍 Running monitoring and risk assessment...")
            
            # Request approval for monitoring check
            approval_result = await request_approval(
                action_type="monitoring_check",
                description="Scan repository for risks, issues, and CI/CD status",
                proposed_action={
                    "repository": self.project_context['repository'],
                    "check_workflows": settings.github_actions_enabled,
                    "check_critical_issues": True,
                    "generate_alerts": True
                },
                risk_level=RiskLevel.LOW,
                context=self.project_context
            )
            
            if approval_result["status"] != "approved":
                return {
                    "success": False,
                    "error": f"Monitoring rejected: {approval_result['message']}"
                }
            
            # Execute monitoring with project context
            result = await self.monitor.perform_health_check()
            
            print("✅ Monitoring check completed successfully")
            return {
                "success": True,
                "result": result,
                "project_context": self.project_context
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    

    
    async def run_full_workflow(self, project_brief: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all PM workflows in sequence.
        
        Args:
            project_brief: Optional project brief for planning
            
        Returns:
            Dictionary with results from all workflows
        """
        print("🚀 Running complete PM agent workflow...")
        
        workflows = {}
        overall_success = True
        
        # Run planning if brief provided
        if project_brief:
            planning_result = await self.run_planning_workflow(project_brief)
            workflows["planning"] = planning_result
            if not planning_result["success"]:
                overall_success = False
        
        # Run daily standup
        standup_result = await self.run_daily_standup()
        workflows["standup"] = standup_result
        if not standup_result["success"]:
            overall_success = False
        
        # Run monitoring
        monitoring_result = await self.run_monitoring_check()
        workflows["monitoring"] = monitoring_result
        if not monitoring_result["success"]:
            overall_success = False
        
        return {
            "overall_success": overall_success,
            "workflows": workflows,
            "project_context": self.project_context
        }
    
    async def handle_github_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitHub webhook events for automated responses.
        
        Args:
            event_type: Type of GitHub event (e.g., "issues", "pull_request")
            payload: Event payload from GitHub
            
        Returns:
            Dictionary with handling results
        """
        try:
            print(f"📨 Handling GitHub webhook: {event_type}")
            
            # Request approval for webhook handling
            approval_result = await request_approval(
                action_type=f"github_webhook_{event_type}",
                description=f"Process GitHub webhook event: {event_type}",
                proposed_action={
                    "event_type": event_type,
                    "repository": payload.get("repository", {}).get("full_name", "unknown"),
                    "action": payload.get("action", "unknown")
                },
                risk_level=RiskLevel.MEDIUM,
                context={"webhook_payload": payload, **self.project_context}
            )
            
            if approval_result["status"] != "approved":
                return {
                    "success": False,
                    "error": f"Webhook handling rejected: {approval_result['message']}"
                }
            
            # Route to appropriate agent based on event type
            if event_type in ["issues", "pull_request"]:
                # Use planner for issue/PR management
                result = await self.planner.plan_project(f"Handle GitHub {event_type} event: {payload}")
            elif event_type in ["workflow_run", "check_run"]:
                # Use monitor for CI/CD events
                result = await self.monitor.perform_health_check()
            else:
                # Default to reporter for general events
                result = await self.reporter.generate_daily_standup()
            
            return {
                "success": True,
                "event_type": event_type,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "event_type": event_type
            }
    
    def get_crew_status(self) -> Dict[str, Any]:
        """Get status of all agents in the crew."""
        return {
            "project_context": self.project_context,
            "agents": {
                "planner": {
                    "name": self.planner.__class__.__name__ if hasattr(self.planner, '__class__') else "PlannerAgent",
                    "status": "active"
                },
                "reporter": {
                    "name": self.reporter.__class__.__name__ if hasattr(self.reporter, '__class__') else "ReporterAgent",
                    "status": "active"
                },
                "monitor": {
                    "name": self.monitor.__class__.__name__ if hasattr(self.monitor, '__class__') else "MonitorAgent",
                    "status": "active"
                }
            },
            "configuration": {
                "human_approval_required": settings.human_approval_required,
                "github_actions_enabled": settings.github_actions_enabled,
                "interactive_mode": settings.interactive_mode
            }
        } 