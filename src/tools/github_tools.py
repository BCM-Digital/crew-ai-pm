"""GitHub tools for PM Agent system."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

import aiohttp
from github import Github
from pydantic import ValidationError

from ..config import settings
from ..schemas import (
    CreateIssueParams, 
    UpdateIssueParams, 
    GitHubIssue, 
    PullRequestParams,
    RiskFlag,
    Priority
)


class GitHubClient:
    """Async GitHub client wrapper."""
    
    def __init__(self):
        self.github = Github(settings.github_token)
        self.repo = self.github.get_repo(f"{settings.github_owner}/{settings.github_repo}")
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make async HTTP request to GitHub API."""
        url = f"https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}{endpoint}"
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with self.session.request(method, url, headers=headers, json=data) as response:
            return await response.json()
    
    async def _make_graphql_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make GraphQL request to GitHub API (for Projects v2)."""
        url = "https://api.github.com/graphql"
        headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        async with self.session.post(url, headers=headers, json=payload) as response:
            return await response.json()
    
    def _format_issue(self, issue) -> GitHubIssue:
        """Convert GitHub issue to our schema."""
        return GitHubIssue(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            labels=[label.name for label in issue.labels],
            assignees=[assignee.login for assignee in issue.assignees],
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            url=issue.html_url
        )


async def create_issue(
    title: str, 
    body: str, 
    labels: List[str] = [], 
    assignees: List[str] = [],
    milestone: Optional[str] = None,
    priority: str = "medium",
    issue_type: str = "task"
) -> Dict[str, Any]:
    """
    Create a new GitHub issue with the specified parameters.
    
    Args:
        title: Issue title
        body: Issue description  
        labels: List of labels to apply
        assignees: List of GitHub usernames to assign
        milestone: Milestone name (optional)
        priority: Issue priority (low, medium, high, critical)
        issue_type: Type of issue (bug, feature, epic, story, task, subtask)
    
    Returns:
        Dictionary with issue details including number and URL
    """
    try:
        async with GitHubClient() as client:
            # Add priority and type to labels
            all_labels = labels + [f"priority:{priority}", f"type:{issue_type}"]
            
            issue = client.repo.create_issue(
                title=title,
                body=body,
                labels=all_labels,
                assignees=assignees
            )
            
            return {
                "success": True,
                "issue_number": issue.number,
                "issue_url": issue.html_url,
                "title": issue.title,
                "labels": [label.name for label in issue.labels]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": "Failed to create GitHub issue"
        }


async def update_issue(
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None, 
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing GitHub issue.
    
    Args:
        issue_number: The issue number to update
        title: New title (optional)
        body: New body content (optional)
        labels: New labels list (optional)
        assignees: New assignees list (optional)
        state: New state - 'open' or 'closed' (optional)
    
    Returns:
        Dictionary with update status and issue details
    """
    try:
        async with GitHubClient() as client:
            issue = client.repo.get_issue(issue_number)
            
            # Update fields that were provided
            if title is not None:
                issue.edit(title=title)
            if body is not None:
                issue.edit(body=body)
            if labels is not None:
                issue.edit(labels=labels)
            if assignees is not None:
                issue.edit(assignees=assignees)
            if state is not None:
                issue.edit(state=state)
            
            return {
                "success": True,
                "issue_number": issue.number,
                "issue_url": issue.html_url,
                "updated_fields": {
                    "title": title,
                    "body": body is not None,
                    "labels": labels,
                    "assignees": assignees,
                    "state": state
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to update issue #{issue_number}"
        }


async def list_issues(
    state: str = "open",
    labels: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    List GitHub issues with optional filtering.
    
    Args:
        state: Issue state ('open', 'closed', 'all')
        labels: Comma-separated label names to filter by
        assignee: GitHub username to filter by assignee
        limit: Maximum number of issues to return
    
    Returns:
        List of issue dictionaries
    """
    try:
        async with GitHubClient() as client:
            issues = client.repo.get_issues(
                state=state,
                labels=labels.split(',') if labels else None,
                assignee=assignee
            )
            
            issue_list = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                    
                issue_data = client._format_issue(issue)
                issue_list.append(issue_data.model_dump())
            
            return issue_list
            
    except Exception as e:
        return [{
            "error": str(e),
            "details": "Failed to list GitHub issues"
        }]


async def search_issues(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search GitHub issues and pull requests using GitHub's search API.
    
    Args:
        query: Search query (e.g., 'is:issue is:open label:bug')
        limit: Maximum number of results
    
    Returns:
        List of matching issues/PRs
    """
    try:
        async with GitHubClient() as client:
            # Add repo qualifier to query
            repo_query = f"{query} repo:{settings.github_owner}/{settings.github_repo}"
            
            results = client.github.search_issues(repo_query)
            
            issue_list = []
            for i, issue in enumerate(results):
                if i >= limit:
                    break
                
                issue_data = client._format_issue(issue)
                issue_list.append(issue_data.model_dump())
            
            return issue_list
            
    except Exception as e:
        return [{
            "error": str(e),
            "details": f"Failed to search issues with query: {query}"
        }]


async def create_pull_request(
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = False
) -> Dict[str, Any]:
    """
    Create a new pull request.
    
    Args:
        title: PR title
        body: PR description
        head: Source branch name
        base: Target branch name
        draft: Whether to create as draft PR
    
    Returns:
        Dictionary with PR details
    """
    try:
        async with GitHubClient() as client:
            pr = client.repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft
            )
            
            return {
                "success": True,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title,
                "state": pr.state,
                "draft": pr.draft
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": "Failed to create pull request"
        }


async def get_repository_stats() -> Dict[str, Any]:
    """
    Get repository statistics and health metrics.
    
    Returns:
        Dictionary with repository stats
    """
    try:
        async with GitHubClient() as client:
            repo = client.repo
            
            # Get basic stats
            stats = {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "size": repo.size,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None
            }
            
            # Get recent activity
            commits = list(repo.get_commits()[:10])
            stats["recent_commits"] = [
                {
                    "sha": commit.sha[:8],
                    "message": commit.commit.message.split('\n')[0],
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat()
                }
                for commit in commits
            ]
            
            return stats
            
    except Exception as e:
        return {
            "error": str(e),
            "details": "Failed to get repository statistics"
        }


async def scan_for_risk_flags(
    search_terms: List[str] = ["blocker", "security", "urgent", "critical", "breaking"]
) -> List[Dict[str, Any]]:
    """
    Scan recent commits, issues, and PRs for risk-indicating keywords.
    
    Args:
        search_terms: List of terms to search for
    
    Returns:
        List of potential risk flags found
    """
    try:
        risk_flags = []
        
        async with GitHubClient() as client:
            # Search in recent commits
            commits = list(client.repo.get_commits()[:50])
            for commit in commits:
                message = commit.commit.message.lower()
                for term in search_terms:
                    if term.lower() in message:
                        risk_flags.append({
                            "type": "commit_risk",
                            "severity": "high" if term in ["security", "critical", "breaking"] else "medium",
                            "description": f"Risk keyword '{term}' found in commit message",
                            "source": "commit",
                            "source_url": commit.html_url,
                            "detected_at": datetime.now().isoformat(),
                            "details": {
                                "commit_sha": commit.sha[:8],
                                "commit_message": commit.commit.message.split('\n')[0],
                                "author": commit.commit.author.name,
                                "keyword": term
                            }
                        })
            
            # Search in recent issues and PRs
            for term in search_terms:
                query = f"is:open {term}"
                results = list(client.github.search_issues(
                    f"{query} repo:{settings.github_owner}/{settings.github_repo}"
                ))[:10]
                
                for item in results:
                    risk_flags.append({
                        "type": "issue_risk",
                        "severity": "high" if term in ["security", "critical", "breaking"] else "medium", 
                        "description": f"Risk keyword '{term}' found in issue/PR",
                        "source": "issue" if not hasattr(item, 'pull_request') else "pull_request",
                        "source_url": item.html_url,
                        "detected_at": datetime.now().isoformat(),
                        "details": {
                            "number": item.number,
                            "title": item.title,
                            "state": item.state,
                            "keyword": term
                        }
                    })
        
        return risk_flags
        
    except Exception as e:
        return [{
            "error": str(e),
            "details": "Failed to scan for risk flags"
        }]


# === GitHub Projects v2 Integration ===

async def get_project_items() -> Dict[str, Any]:
    """
    Get all items (issues/PRs) in the GitHub Project.
    
    Returns:
        Dictionary with project items and their status
    """
    if not settings.github_project_id:
        return {
            "success": False,
            "error": "GitHub Project ID not configured",
            "details": "Set GITHUB_PROJECT_ID in your .env file"
        }
    
    query = """
    query($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                title
                items(first: 100) {
                    nodes {
                        id
                        type
                        content {
                            ... on Issue {
                                number
                                title
                                state
                                labels(first: 10) {
                                    nodes {
                                        name
                                    }
                                }
                                assignees(first: 10) {
                                    nodes {
                                        login
                                    }
                                }
                            }
                            ... on PullRequest {
                                number
                                title
                                state
                                isDraft
                            }
                        }
                        fieldValues(first: 20) {
                            nodes {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                    field {
                                        ... on ProjectV2FieldCommon {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldTextValue {
                                    text
                                    field {
                                        ... on ProjectV2FieldCommon {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        async with GitHubClient() as client:
            result = await client._make_graphql_request(query, {"projectId": settings.github_project_id})
            
            if "errors" in result:
                return {
                    "success": False,
                    "error": result["errors"][0]["message"],
                    "details": "GraphQL query failed"
                }
            
            project = result["data"]["node"]
            items = []
            
            for item in project["items"]["nodes"]:
                if item["content"]:
                    content = item["content"]
                    item_data = {
                        "id": item["id"],
                        "type": item["type"].lower(),
                        "number": content.get("number"),
                        "title": content.get("title"),
                        "state": content.get("state"),
                        "is_draft": content.get("isDraft", False),
                        "fields": {}
                    }
                    
                    # Extract custom field values
                    for field_value in item["fieldValues"]["nodes"]:
                        if field_value:
                            field_name = field_value.get("field", {}).get("name", "")
                            if "name" in field_value:  # Single select
                                item_data["fields"][field_name] = field_value["name"]
                            elif "text" in field_value:  # Text
                                item_data["fields"][field_name] = field_value["text"]
                    
                    items.append(item_data)
            
            return {
                "success": True,
                "project_title": project["title"],
                "items": items,
                "total_items": len(items)
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": "Failed to fetch GitHub Project items"
        }


async def update_project_item_status(item_id: str, status: str) -> Dict[str, Any]:
    """
    Update the status of an item in GitHub Project.
    
    Args:
        item_id: GitHub Project item ID
        status: New status (e.g., "Todo", "In Progress", "Done")
    
    Returns:
        Dictionary with update status
    """
    # This requires getting the field ID first, then updating
    # Implementation would be more complex in practice
    return {
        "success": False,
        "error": "Not implemented",
        "details": "GitHub Projects v2 field updates require field schema discovery"
    }


# === GitHub Actions Integration ===

async def get_workflow_runs(workflow_file: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Get recent workflow runs for the repository.
    
    Args:
        workflow_file: Specific workflow file to filter by (optional)
        limit: Maximum number of runs to return
    
    Returns:
        Dictionary with workflow run details
    """
    try:
        async with GitHubClient() as client:
            endpoint = "/actions/runs"
            if workflow_file:
                endpoint += f"?workflow={workflow_file}"
            
            response = await client._make_request("GET", endpoint)
            
            runs = []
            for run in response.get("workflow_runs", [])[:limit]:
                runs.append({
                    "id": run["id"],
                    "name": run["name"],
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                    "created_at": run["created_at"],
                    "updated_at": run["updated_at"],
                    "head_branch": run["head_branch"],
                    "head_sha": run["head_sha"][:8],
                    "url": run["html_url"],
                    "triggering_actor": run.get("triggering_actor", {}).get("login", "unknown")
                })
            
            return {
                "success": True,
                "runs": runs,
                "total_count": response.get("total_count", len(runs))
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": "Failed to fetch workflow runs"
        }


async def trigger_workflow(workflow_file: str, ref: str = "main", inputs: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Trigger a GitHub Actions workflow.
    
    Args:
        workflow_file: Workflow file name (e.g., "ci.yml")
        ref: Git reference to run workflow on (default: "main")
        inputs: Optional workflow inputs
    
    Returns:
        Dictionary with trigger status
    """
    try:
        async with GitHubClient() as client:
            endpoint = f"/actions/workflows/{workflow_file}/dispatches"
            data = {
                "ref": ref,
                "inputs": inputs or {}
            }
            
            response = await client._make_request("POST", endpoint, data)
            
            return {
                "success": True,
                "message": f"Workflow {workflow_file} triggered successfully",
                "ref": ref,
                "inputs": inputs
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to trigger workflow {workflow_file}"
        }


async def get_repository_health() -> Dict[str, Any]:
    """
    Get comprehensive repository health metrics including CI/CD status.
    
    Returns:
        Dictionary with repository health information
    """
    try:
        async with GitHubClient() as client:
            # Get recent workflow runs
            workflows_result = await get_workflow_runs(limit=5)
            
            # Get repository stats
            repo_stats = await get_repository_stats()
            
            # Get recent issues and PRs
            issues = await list_issues(state="all", limit=10)
            
            # Calculate health metrics
            recent_failures = 0
            if workflows_result["success"]:
                for run in workflows_result["runs"]:
                    if run["conclusion"] == "failure":
                        recent_failures += 1
            
            open_critical_issues = len([
                issue for issue in issues 
                if any("critical" in str(label).lower() for label in issue.get("labels", []))
                and issue.get("state") == "open"
            ])
            
            health_score = max(0, 100 - (recent_failures * 20) - (open_critical_issues * 30))
            
            return {
                "success": True,
                "health_score": health_score,
                "recent_workflow_failures": recent_failures,
                "open_critical_issues": open_critical_issues,
                "repository_stats": repo_stats,
                "recent_workflows": workflows_result.get("runs", []),
                "assessment": "Healthy" if health_score > 80 else "Needs Attention" if health_score > 50 else "Critical"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": "Failed to assess repository health"
        } 