"""Configuration management for the PM Agent system."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    
    # GitHub Configuration
    github_token: str = Field(..., description="GitHub personal access token")
    github_owner: str = Field(..., description="GitHub repository owner")
    github_repo: str = Field(..., description="GitHub repository name")
    
    # GitHub Projects Configuration
    github_project_id: str = Field(default="", description="GitHub Project ID (found in project URL)")
    github_project_number: int = Field(default=1, description="GitHub Project number")
    
    # Project Context Configuration
    project_name: str = Field(..., description="Human-readable project name")
    project_description: str = Field(default="", description="Brief description of the project")
    current_sprint: str = Field(default="", description="Current sprint/milestone identifier")
    team_members: str = Field(default="", description="Comma-separated list of team member GitHub usernames")
    
    # Slack Configuration
    slack_bot_token: str = Field(..., description="Slack bot token")
    slack_app_token: str = Field(default="", description="Slack app token for socket mode")
    slack_channel: str = Field(default="#pm-updates", description="Default Slack channel for updates")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./pm_agent.db", description="Database connection URL")
    
    # Vector Store Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", description="ChromaDB persistence directory")
    
    # Agent Configuration
    agent_verbose: bool = Field(default=True, description="Enable verbose agent logging")
    max_execution_time: int = Field(default=300, description="Maximum execution time in seconds")
    
    # Human-in-the-Loop Configuration
    human_approval_required: bool = Field(default=True, description="Require human approval for critical actions")
    interactive_mode: bool = Field(default=False, description="Enable interactive chat mode with crew")
    approval_timeout: int = Field(default=300, description="Timeout for human approval in seconds")
    auto_approve_low_risk: bool = Field(default=False, description="Auto-approve low-risk actions")
    
    # CI/CD Configuration (GitHub Actions)
    github_actions_enabled: bool = Field(default=True, description="Enable GitHub Actions integration")
    main_workflow_file: str = Field(default=".github/workflows/ci.yml", description="Main CI workflow file")
    deployment_workflow_file: str = Field(default=".github/workflows/deploy.yml", description="Deployment workflow file")

    @property
    def team_member_list(self) -> list[str]:
        """Get team members as a list."""
        if not self.team_members:
            return []
        return [member.strip() for member in self.team_members.split(',') if member.strip()]

    def get_project_context(self) -> dict:
        """Get complete project context for agents."""
        return {
            "project_name": self.project_name,
            "project_description": self.project_description,
            "repository": f"{self.github_owner}/{self.github_repo}",
            "github_project_id": self.github_project_id,
            "current_sprint": self.current_sprint,
            "team_members": self.team_member_list,
            "slack_channel": self.slack_channel
        }


# Global settings instance
settings = Settings() 