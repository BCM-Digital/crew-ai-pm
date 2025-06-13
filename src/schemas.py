"""Pydantic schemas for PM Agent system data structures."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Issue priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """GitHub issue types."""
    BUG = "bug"
    FEATURE = "feature"
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"


class IssueStatus(str, Enum):
    """Issue status states."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"


# GitHub Tool Schemas
class CreateIssueParams(BaseModel):
    """Parameters for creating a GitHub issue."""
    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue description")
    labels: List[str] = Field(default=[], description="Issue labels")
    assignees: List[str] = Field(default=[], description="Issue assignees")
    milestone: Optional[str] = Field(None, description="Milestone name")
    priority: Priority = Field(default=Priority.MEDIUM, description="Issue priority")
    issue_type: IssueType = Field(default=IssueType.TASK, description="Issue type")


class UpdateIssueParams(BaseModel):
    """Parameters for updating a GitHub issue."""
    issue_number: int = Field(..., description="Issue number")
    title: Optional[str] = Field(None, description="New issue title")
    body: Optional[str] = Field(None, description="New issue description")
    labels: Optional[List[str]] = Field(None, description="New issue labels")
    assignees: Optional[List[str]] = Field(None, description="New issue assignees")
    state: Optional[str] = Field(None, description="Issue state (open/closed)")


class GitHubIssue(BaseModel):
    """GitHub issue representation."""
    number: int
    title: str
    body: str
    state: str
    labels: List[str]
    assignees: List[str]
    created_at: datetime
    updated_at: datetime
    url: str


class PullRequestParams(BaseModel):
    """Parameters for GitHub pull request operations."""
    title: str = Field(..., description="Pull request title")
    body: str = Field(..., description="Pull request description")
    head: str = Field(..., description="Source branch")
    base: str = Field(default="main", description="Target branch")
    draft: bool = Field(default=False, description="Create as draft PR")


# Slack Tool Schemas
class SlackMessageParams(BaseModel):
    """Parameters for sending Slack messages."""
    channel: str = Field(..., description="Slack channel (e.g., #general)")
    text: str = Field(..., description="Message text")
    blocks: Optional[List[Dict[str, Any]]] = Field(None, description="Slack blocks for rich formatting")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for replies")


class SlackApprovalParams(BaseModel):
    """Parameters for Slack approval requests."""
    channel: str = Field(..., description="Slack channel")
    title: str = Field(..., description="Approval request title")
    description: str = Field(..., description="What needs approval")
    action_data: Dict[str, Any] = Field(..., description="Data for the action being approved")
    requester: str = Field(..., description="Who is requesting approval")


# Project Management Schemas
class Sprint(BaseModel):
    """Sprint representation."""
    id: str
    name: str
    start_date: datetime
    end_date: datetime
    capacity: int
    current_story_points: int = 0
    status: str = "active"


class StoryPoint(BaseModel):
    """Story point estimation."""
    issue_number: int
    points: int
    complexity: str
    estimated_hours: Optional[float] = None


class ProjectBrief(BaseModel):
    """Project brief for planning."""
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Project description")
    requirements: List[str] = Field(..., description="List of requirements")
    deadline: Optional[datetime] = Field(None, description="Project deadline")
    priority: Priority = Field(default=Priority.MEDIUM, description="Project priority")
    stakeholders: List[str] = Field(default=[], description="Project stakeholders")


class TaskBreakdown(BaseModel):
    """Task breakdown structure."""
    epics: List[CreateIssueParams] = Field(..., description="Epic-level issues")
    stories: List[CreateIssueParams] = Field(..., description="Story-level issues")
    tasks: List[CreateIssueParams] = Field(..., description="Task-level issues")
    estimated_effort: Dict[str, int] = Field(..., description="Effort estimates by category")


# Monitoring & Reporting Schemas
class CIStatus(BaseModel):
    """CI/CD pipeline status."""
    pipeline_id: str
    status: str  # success, failure, pending, cancelled
    branch: str
    commit_sha: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    logs_url: Optional[str] = None


class RiskFlag(BaseModel):
    """Risk flag for monitoring."""
    id: str
    type: str  # blocker, security, performance, deadline
    severity: Priority
    description: str
    source: str  # commit, issue, pr, pipeline
    source_url: str
    detected_at: datetime
    resolved: bool = False


class StandupReport(BaseModel):
    """Daily standup report."""
    date: datetime
    team_members: List[str]
    completed_yesterday: List[str]
    planned_today: List[str]
    blockers: List[RiskFlag]
    sprint_progress: Dict[str, Any]
    burn_down_data: Dict[str, int]


class SprintReport(BaseModel):
    """Sprint summary report."""
    sprint: Sprint
    completed_stories: List[GitHubIssue]
    incomplete_stories: List[GitHubIssue]
    team_velocity: int
    burn_down_chart: Dict[str, int]
    retrospective_notes: List[str] 