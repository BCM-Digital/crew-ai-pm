"""Monitor Agent - Watches CI/CD pipelines and raises alerts."""

from .base_agent import BaseAgent
from ..tools.github_tools import scan_for_risk_flags, get_repository_stats
from ..tools.slack_tools import send_message


class MonitorAgent(BaseAgent):
    """Agent responsible for monitoring system health and risks."""
    
    def __init__(self):
        super().__init__(
            role="System Monitor",
            goal="""Monitor CI/CD pipelines, code quality metrics, and system health.
                    Proactively identify and alert on potential issues, failures, 
                    and risks before they impact the team.""",
            backstory="""You are a vigilant system administrator with deep experience 
                        in DevOps and monitoring. You have an eye for patterns that 
                        indicate trouble and can quickly escalate issues to the right 
                        people with actionable information.""",
            tools=[scan_for_risk_flags, get_repository_stats, send_message]
        )
    
    async def perform_health_check(self) -> dict:
        """Perform a comprehensive system health check."""
        task_description = """
        Perform a comprehensive system health check and risk assessment:
        
        1. Scan recent commits and issues for risk keywords
        2. Check repository health metrics
        3. Identify potential security or stability concerns
        4. Assess any critical issues found
        5. Provide recommendations for addressing risks
        
        Focus on identifying issues that could impact development velocity,
        system stability, or security. Prioritize by severity and urgency.
        """
        
        return await self.execute_task(task_description)
    
    async def scan_risks(self, search_terms: list = None) -> dict:
        """Scan for specific risk patterns."""
        if search_terms is None:
            search_terms = ["blocker", "security", "urgent", "critical", "breaking"]
        
        task_description = f"""
        Scan the repository for risk indicators using these terms: {', '.join(search_terms)}
        
        1. Search recent commits for these keywords
        2. Check open issues and PRs for risk indicators
        3. Analyze the severity and context of findings
        4. Determine which findings require immediate attention
        5. Recommend actions for each risk identified
        
        Provide specific, actionable recommendations for each risk found.
        """
        
        return await self.execute_task(task_description)


def create_monitor_agent() -> MonitorAgent:
    """Create and return a monitor agent instance."""
    return MonitorAgent() 