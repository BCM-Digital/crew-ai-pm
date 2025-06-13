# PM Agent System

An AI-powered Project Management Agent system that automates routine PM tasks using AI agents with human-in-the-loop supervision.

## 🎯 Overview

The PM Agent System provides intelligent project management automation with:

- **Project Context Awareness**: Automatically knows which project it's working on
- **Human-in-the-Loop Interaction**: Real-time approval and modification of agent actions
- **GitHub Integration**: Native support for GitHub Projects, Issues, PRs, and Actions
- **Multi-Agent Architecture**: Specialized agents for planning, reporting, and monitoring
- **Interactive CLI**: Real-time collaboration with your PM crew

## 🌟 Features

### Multi-Agent Architecture
- **Planner Agent**: Converts project briefs into structured GitHub issues and task breakdowns
- **Reporter Agent**: Generates daily standups and sprint reports automatically  
- **Monitor Agent**: Watches CI/CD pipelines and scans for risk flags

### Automated Workflows
- ✅ **Project Planning**: Break down features into epics, stories, and tasks
- 📊 **Daily Standups**: Auto-generate status reports from GitHub activity
- 🔍 **Risk Monitoring**: Scan commits and issues for security/blocker keywords
- 📈 **Sprint Reports**: Track velocity and completion metrics

### Integrations
- **GitHub**: Issue management, PR tracking, repository analytics
- **Slack**: Team notifications, approval workflows, status updates
- **OpenAI**: GPT-4 powered reasoning and natural language processing

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd crew-ai-pm

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp config.example.env .env
```

### 2. Configuration

Edit your `.env` file with your project details:

```bash
# Project Context - Tell the crew which project it's managing
PROJECT_NAME=My Awesome Project
PROJECT_DESCRIPTION=A brief description of what this project does
CURRENT_SPRINT=Sprint 2024-Q1-3
TEAM_MEMBERS=alice,bob,charlie

# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_OWNER=your_github_username_or_org
GITHUB_REPO=your_repository_name
GITHUB_PROJECT_ID=PVT_kwDOABCD1234567890  # Optional: GitHub Project ID

# AI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Slack Configuration (Optional)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_CHANNEL=#pm-updates

# Human Interaction Settings
HUMAN_APPROVAL_REQUIRED=true
INTERACTIVE_MODE=false
AUTO_APPROVE_LOW_RISK=false
```

### 3. Getting Your GitHub Project ID

To enable GitHub Projects integration:

1. Go to your GitHub Project
2. Copy the Project ID from the URL: `https://github.com/users/USERNAME/projects/NUMBER`
3. Or use GraphQL API to get the Project ID

### 4. Usage

#### Interactive Mode (Recommended)

Start real-time collaboration with your PM crew:

```bash
python main.py interactive
```

Available interactive commands:
- `status` - Show current project status from GitHub Projects
- `standup` - Generate daily standup report
- `monitor` - Run risk assessment and health check
- `plan <brief>` - Plan a new feature or project
- `project` - Show detailed project information
- `workflows` - Show recent GitHub Actions runs
- `health` - Show repository health metrics
- `team` - Show team member information
- `config` - Show current configuration
- `history` - Show human interaction history
- `help` - Show all available commands

#### Command Line Interface

Run specific workflows:

```bash
# Plan a new feature
python main.py plan "Add user authentication system"

# Generate standup report
python main.py standup

# Run monitoring check
python main.py monitor

# Run all workflows
python main.py run-all

# Show configuration
python main.py config

# Test connections
python main.py test
```

## 🤝 Human-in-the-Loop Features

The system includes sophisticated human oversight:

### Approval Workflow

When agents want to take actions, you'll see:

```
============================================================
🤝 Human Approval Required

Action: create_github_issue
Risk Level: MEDIUM
Description: Create issue for user authentication feature

Proposed Action Details:
  title: "Implement user authentication"
  body: "Add login/logout functionality..."
  assignees: ["alice", "bob"]
  labels: ["feature", "high-priority"]

Options:
  a - Approve action as proposed
  r - Reject action
  m - Modify action parameters
  s - Skip (auto-approve for this session)

What would you like to do? [a]:
```

### Modification Capabilities

You can modify any proposed action:

```
Modify Action Parameters:
Current parameters:
  title: Implement user authentication
  assignees: ["alice", "bob"]

Options:
  <key>=<value> - Set parameter
  done - Finish modifications
  cancel - Cancel modifications

Enter modification: assignees=["charlie"]
Set assignees = ["charlie"]

Enter modification: done
```

## 🔧 Architecture

### Agents

- **PlannerAgent**: Breaks down projects into tasks, creates issues, assigns work
- **ReporterAgent**: Generates standup reports, sprint summaries, status updates
- **MonitorAgent**: Scans for risks, monitors CI/CD, checks repository health

### Project Context Integration

Every agent automatically knows:
- Which project it's working on
- Team member GitHub usernames
- Current sprint/milestone
- GitHub repository and project details
- Slack channels for communication

### GitHub Integration

- **Issues & PRs**: Create, update, and manage development work
- **GitHub Projects**: Track progress using native GitHub project boards
- **GitHub Actions**: Monitor CI/CD pipelines and trigger workflows
- **Repository Health**: Assess code quality, security, and performance

## 📊 Features in Detail

### Project Status Monitoring

Get real-time project insights:

```bash
python main.py interactive
> status
```

Shows:
- GitHub Project board status
- Issue breakdown by status
- Recent activity
- Team workload distribution

### Workflow Integration

Monitor your CI/CD pipelines:

```bash
> workflows
```

Shows:
- Recent workflow runs
- Success/failure rates
- Performance metrics
- Deployment status

### Repository Health

Assess overall project health:

```bash
> health
```

Provides:
- Health score (0-100)
- Recent failures
- Critical issues
- Security alerts
- Performance metrics

## 🛠 Advanced Configuration

### Risk Level Settings

Configure automatic approval for different risk levels:

```env
# Auto-approve low-risk actions (creating labels, minor updates)
AUTO_APPROVE_LOW_RISK=true

# Require approval for all actions
HUMAN_APPROVAL_REQUIRED=true

# Timeout for approval requests (seconds)
APPROVAL_TIMEOUT=300
```

### GitHub Actions Integration

```env
# Enable GitHub Actions monitoring
GITHUB_ACTIONS_ENABLED=true

# Specify workflow files to monitor
MAIN_WORKFLOW_FILE=.github/workflows/ci.yml
DEPLOYMENT_WORKFLOW_FILE=.github/workflows/deploy.yml
```

## 📈 Workflow Examples

### Daily Standup Flow

1. Agent scans GitHub repository for recent activity
2. Requests approval to generate standup report
3. Fetches data from GitHub Projects, Issues, and PRs
4. Generates formatted report
5. Posts to Slack (with approval)

### Project Planning Flow

1. Human provides project brief via interactive mode
2. Agent requests approval for planning action
3. Breaks down project into tasks and issues
4. Creates GitHub issues with proper assignments
5. Updates project board status
6. Notifies team via Slack

### Risk Monitoring Flow

1. Agent scans repository for risk indicators
2. Checks CI/CD pipeline health
3. Identifies critical issues or security alerts
4. Requests approval for alerting team
5. Creates urgent issues or notifications

## 🔒 Security & Privacy

- All actions require human approval by default
- Sensitive operations use higher risk levels
- API keys are securely managed via environment variables
- No data is stored outside your environment
- Full audit trail of all interactions

## 🚦 Getting Started Tips

1. **Start Small**: Begin with `HUMAN_APPROVAL_REQUIRED=true` to see all actions
2. **Use Interactive Mode**: It's the best way to collaborate with agents
3. **Configure Project Context**: This makes agents much more effective
4. **Set Up GitHub Projects**: Native integration provides the best experience
5. **Monitor Interactions**: Use `history` command to see what agents are doing

## 🤔 Troubleshooting

### Common Issues

**"GitHub Project ID not configured"**
- Set `GITHUB_PROJECT_ID` in your `.env` file
- Find it in your GitHub Project URL

**"Human approval required but no response"**
- Check your `APPROVAL_TIMEOUT` setting
- Use interactive mode for better experience

**"Permission denied"**
- Verify GitHub token has required permissions
- Check repository access

### Debug Mode

Enable verbose logging:

```env
AGENT_VERBOSE=true
```

## 📚 API Reference

### Project Context Object

```python
{
    "project_name": "My Awesome Project",
    "project_description": "Description...",
    "repository": "owner/repo",
    "github_project_id": "PVT_kwDO...",
    "current_sprint": "Sprint 2024-Q1-3",
    "team_members": ["alice", "bob"],
    "slack_channel": "#pm-updates"
}
```

### Human Approval Response

```python
{
    "status": "approved|rejected|modified|timeout",
    "action": {...},  # Approved/modified action
    "message": "User feedback"
}
```

## 🎉 What's Next?

This system gives you:

- ✅ **Project Context Awareness**: Agents know exactly which project they're managing
- ✅ **Human-in-the-Loop Control**: Approve, reject, or modify any agent action
- ✅ **GitHub Native Integration**: Works seamlessly with GitHub Projects and Actions
- ✅ **Interactive Collaboration**: Real-time chat with your PM crew
- ✅ **Intelligent Automation**: Sophisticated AI with human oversight

The PM Agent System transforms how you manage projects by combining AI intelligence with human judgment, all while maintaining full control and transparency.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- 📚 Check the [documentation](docs/) for detailed guides
- 🐛 Report bugs via [GitHub Issues](issues)
- 💬 Join discussions in [GitHub Discussions](discussions)
- 📧 Contact: [your-email@example.com](mailto:your-email@example.com)

---

**Built with ❤️ using [CrewAI](https://github.com/crewAIInc/crewAI)** 