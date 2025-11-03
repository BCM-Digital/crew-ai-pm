# PM Agent on AgentCore

Production-ready personal PM Agent on Amazon Bedrock AgentCore with sub-agents, Gateway tools, approvals, work-graph store, and web UI.

## Features

- **Intelligent Planning**: Ingests work signals from email, calendar, Planner, Teams, and GitHub
- **Draft by Default**: All sends and changes require explicit approval via Teams Adaptive Cards
- **Work Graph**: Tracks tasks, people, documents, and relationships in Aurora Postgres
- **Strong Guardrails**: Token budgets, cost guards, approval-bound actions, PII redaction
- **Full Observability**: Structured logs, CloudWatch dashboards, alarms

## Architecture

- **AgentCore Supervisor** with memory and policies
- **Collaborators**: Planner, Comms, Tracker, Dispatcher (optional)
- **Gateway Tools**: Strict JSON schemas, idempotency, retries
- **Tool Adapters**: Python 3.12 Lambdas with AWS Powertools
- **Work Graph**: Aurora Serverless v2 (Postgres)
- **Approvals**: Teams Adaptive Cards with short-lived, action-bound tokens
- **Events**: EventBridge schedules (Brisbane timezone)
- **UI**: Next.js 14 with App Router

## Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js 20+ and pnpm
- Python 3.12+
- PostgreSQL client (psql)
- AWS CDK v2 bootstrapped in target region

## Quick Start

```bash
# Install dependencies
make bootstrap

# Copy and configure
cp config/app.example.yaml config/app.yaml
cp config/projects.example.yaml config/projects.yaml
cp config/features.example.yaml config/features.yaml
# Edit config files with your values

# Deploy infrastructure
make deploy

# Run database migrations
export DATABASE_URL="postgresql://user:pass@host/db"
make db:migrate

# Run smoke test
make smoke
```

## Configuration

Edit `config/app.yaml` with:
- M365 tenant ID, client ID, and secret SSM paths
- Teams DM chat ID for notifications
- Project list matching your Planner
- Schedules in Brisbane local time
- Cost guards (token limits)

## Flows

### Plan Day (07:30 Brisbane)
1. Lists flagged emails and today's calendar
2. Generates daily plan with top 5 tasks, risks, approvals needed
3. Posts Teams card for approval
4. Creates calendar holds and Planner tasks on approval

### Blocker Sweep (Every 2 hours)
1. Scans Planner for tasks waiting/blocked > 48 hours
2. Drafts polite nudges
3. Requires approval for external emails

### Status Pack (15:30 Brisbane)
1. Queries task changes per project since last status
2. Generates client update bullets
3. Drafts Outlook emails
4. Sends on approval

## Approval System

All create/send actions require a short-lived approval token:
- Token bound to action hash (subject, body, recipients, times)
- 10-minute TTL (configurable)
- Single use only
- Payload changes rejected

## Cost Controls

- Max 200k tokens per run
- Max 200 tool invocations per run
- Monthly stop after 20M tokens
- Configurable in `config/app.yaml`

## Observability

- **Logs**: Structured JSON with trace_id, run_id, tool, latency_ms, ok, error_code
- **Metrics**: p95 latency per tool, error rates, invocation counts, token spend
- **Alarms**: Error rate spikes, approval failures, DB saturation
- **Dashboard**: `/ops/dashboards.json`

## Security

- IAM roles per tool group (least privilege)
- Secrets in Secrets Manager with KMS CMK
- API Gateway with WAF basic rules
- PII redaction in logs
- Feature flags for safe rollout

## Development

```bash
# Synth CDK
make synth

# Run tests
pnpm test              # Infrastructure tests
pytest                 # Lambda and flow tests

# Lint and format
make lint
make format
```

## CI/CD

GitHub Actions workflows:
- **infra.yml**: CDK synth, diff, deploy with review gates
- **tests.yml**: Python tests, schema checks, TypeScript builds, pre-commit
- **security.yml**: cdk-nag, cfn-nag, bandit, npm audit
- **Go/No-Go**: Blocks deploy on test failures or high security findings

## Project Structure

```
/infra          CDK and CloudFormation IaC
/lambdas        Tool adapter Lambdas (M365, GitHub, Jira, DevOps, KB)
/runtime        Prompts, flows, schemas, DB client
/ui             Next.js web interface
/tests          Unit, integration, and smoke tests
/ops            Runbooks, dashboards, alarms
/config         Configuration files
```

## Operational Runbooks

See `/ops/runbooks.md` for:
- Emergency response procedures
- Common troubleshooting steps
- Approval token debugging
- Cost spike investigation
- Database maintenance

## Support

For issues or questions, see `/ops/runbooks.md` or contact the platform team.

## License

Proprietary - Internal Use Only
