"""Planner Agent - Converts project briefs into structured tasks and issues."""

from .base_agent import BaseAgent
from ..tools.github_tools import create_issue, search_issues
from ..tools.slack_tools import send_message


class PlannerAgent(BaseAgent):
    """Agent responsible for project planning and task breakdown."""
    
    def __init__(self):
        super().__init__(
            role="Project Planner",
            goal="""Transform project briefs and feature requests into well-structured 
                    epics, stories, and tasks with clear acceptance criteria and estimates.
                    Break down complex requirements into manageable work items.""",
            backstory="""You are an experienced technical project manager with expertise in 
                        agile methodologies. You excel at taking high-level requirements 
                        and breaking them down into concrete, actionable tasks. You understand 
                        software development workflows and can estimate complexity accurately.""",
            tools=[create_issue, search_issues, send_message]
        )
    
    async def plan_project(self, project_brief: str) -> dict:
        """Plan a project from a brief description."""
        task_description = f"""
        Analyze the following project brief and create a comprehensive task breakdown:
        
        Project Brief: {project_brief}
        
        Please provide:
        1. A breakdown into epics, stories, and tasks
        2. Estimated effort and complexity for each item
        3. Identification of dependencies and risks
        4. Recommended GitHub issues to create
        5. A summary of the planning results
        
        Format your response in a structured way that can be easily understood and acted upon.
        """
        
        return await self.execute_task(task_description)


def create_planner_agent() -> PlannerAgent:
    """Create and return a planner agent instance."""
    return PlannerAgent() 