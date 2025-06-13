"""Reporter Agent - Generates daily standups and sprint reports."""

from .base_agent import BaseAgent
from ..tools.github_tools import list_issues, get_repository_stats
from ..tools.slack_tools import send_message


class ReporterAgent(BaseAgent):
    """Agent responsible for generating reports and status updates."""
    
    def __init__(self):
        super().__init__(
            role="Sprint Reporter",
            goal="""Generate comprehensive daily standup reports and sprint summaries.
                    Track team progress, identify blockers, and communicate status 
                    clearly to stakeholders.""",
            backstory="""You are a detail-oriented project coordinator who excels at 
                        synthesizing information from multiple sources into clear, 
                        actionable reports. You understand team dynamics and can 
                        identify potential issues before they become blockers.""",
            tools=[list_issues, get_repository_stats, send_message]
        )
    
    async def generate_daily_standup(self) -> dict:
        """Generate a daily standup report."""
        task_description = """
        Generate a daily standup report for today. Please:
        
        1. Review recent GitHub activity (issues, PRs, commits)
        2. Identify completed work from yesterday
        3. List planned work for today
        4. Identify any blockers or concerns
        5. Calculate sprint progress metrics
        6. Format the report for Slack posting
        
        Provide a comprehensive but concise status update that would be valuable 
        for a development team's daily standup meeting.
        """
        
        return await self.execute_task(task_description)
    
    async def generate_sprint_report(self, sprint_name: str) -> dict:
        """Generate a sprint summary report."""
        task_description = f"""
        Generate a comprehensive sprint report for: {sprint_name}
        
        Please analyze:
        1. Sprint metrics and completion rates
        2. Completed vs incomplete work
        3. Team velocity and performance
        4. Key achievements and challenges
        5. Recommendations for next sprint
        
        Format this as a professional sprint summary suitable for stakeholders.
        """
        
        return await self.execute_task(task_description)


def create_reporter_agent() -> ReporterAgent:
    """Create and return a reporter agent instance."""
    return ReporterAgent() 