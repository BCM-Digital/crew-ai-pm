# PM Agent Deployment Guide

Complete guide for deploying PM Agent on AWS with Amazon Bedrock AgentCore.

## Prerequisites

- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- Node.js 20+ and pnpm installed
- Python 3.12+ installed
- PostgreSQL client (psql) installed
- Microsoft 365 tenant with admin access (for Graph API)
- GitHub account with personal access token

## Pre-Deployment Checklist

- [ ] AWS CDK v2 bootstrapped in target region
- [ ] M365 App Registration created in Azure Portal
- [ ] GitHub Personal Access Token generated
- [ ] Reviewed cost estimates and budgets
- [ ] Configured AWS credentials locally

## Step 1: AWS CDK Bootstrap

If not already bootstrapped in `ap-southeast-2`:

```bash
export AWS_REGION=ap-southeast-2
export AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
```

## Step 2: Microsoft 365 App Registration

### Create App Registration

1. Go to [Azure Portal](https://portal.azure.com/) → Azure Active Directory → App registrations
2. Click "New registration"
3. Name: "PM Agent"
4. Supported account types: "Single tenant"
5. Redirect URI: Leave empty (not needed for daemon app)
6. Click "Register"

### Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission" → "Microsoft Graph" → "Application permissions"
3. Add the following permissions:
   - `Mail.Read`
   - `Mail.Send`
   - `Calendars.ReadWrite`
   - `Tasks.ReadWrite`
   - `Sites.ReadWrite.All`
   - `Chat.Read`
   - `ChatMessage.Send`
4. Click "Grant admin consent for [your tenant]"

### Create Client Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Description: "PM Agent"
4. Expires: 24 months (recommended)
5. Click "Add"
6. **IMPORTANT**: Copy the secret value immediately (it won't be shown again)

### Note Configuration Values

Copy these values for later:
- **Tenant ID**: From "Overview" page
- **Client ID**: From "Overview" page (Application ID)
- **Client Secret**: From previous step

## Step 3: GitHub Personal Access Token

1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Scopes: `repo`, `read:org`, `read:user`
4. Click "Generate token"
5. Copy the token value

## Step 4: Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd crew-ai-pm

# Install dependencies
make bootstrap

# Copy configuration files
cp config/app.example.yaml config/app.yaml
cp config/projects.example.yaml config/projects.yaml
cp config/features.example.yaml config/features.yaml
```

## Step 5: Update Configuration

### Edit `config/app.yaml`

```yaml
env: dev
region: ap-southeast-2
timezone: Australia/Brisbane
use_postgres: true

projects:
  - MCU
  - QRIDA
  - "Uniform Link"
  - LTC
  - SureMesh

m365:
  tenant_id: "<YOUR_TENANT_ID>"
  client_id: "<YOUR_CLIENT_ID>"
  client_secret_ssm: "/pm-agent/m365/client-secret"
  teams_dm_chat_id_ssm: "/pm-agent/m365/damien-dm-chat-id"

# Rest of config...
```

### Edit `config/projects.yaml`

Update project names and Planner plan names to match your environment.

### Edit `config/features.yaml`

Start with conservative settings:

```yaml
flags:
  send_emails: false              # Disable until tested
  create_calendar_holds: false    # Disable until tested
  create_planner_tasks: false     # Disable until tested
  jira_enabled: false
```

## Step 6: Deploy Infrastructure

```bash
# Synthesise CDK (check for errors)
make synth

# Review changes
cd infra/cdk
pnpm cdk diff

# Deploy all stacks
make deploy
```

This will deploy:
- VPC with S3/DynamoDB gateway endpoints
- Security (IAM roles, KMS key)
- Secrets (placeholder values - update next)
- Database (Aurora Serverless v2 Postgres)
- Lambdas (M365, GitHub tool adapters)
- EventBridge (scheduled rules)
- Observability (CloudWatch dashboard, alarms)

**Deployment time**: ~15-20 minutes

## Step 7: Update Secrets

After deployment, update the placeholder secrets:

```bash
# Update M365 client secret
aws secretsmanager update-secret \
  --secret-id /pm-agent/m365/client-secret \
  --secret-string "<YOUR_M365_CLIENT_SECRET>" \
  --region ap-southeast-2

# Update GitHub token
aws secretsmanager update-secret \
  --secret-id /pm-agent/github/token \
  --secret-string "<YOUR_GITHUB_TOKEN>" \
  --region ap-southeast-2
```

## Step 8: Configure SSM Parameters

### Get Teams DM Chat ID

1. In Teams, send a message to yourself or the bot
2. Use Microsoft Graph Explorer to get chat ID:
   ```
   GET https://graph.microsoft.com/v1.0/me/chats
   ```
3. Find the chat ID for your DM

```bash
# Store Teams DM chat ID
aws ssm put-parameter \
  --name /pm-agent/m365/damien-dm-chat-id \
  --type String \
  --value "<YOUR_TEAMS_CHAT_ID>" \
  --region ap-southeast-2
```

## Step 9: Database Migration

Get the database endpoint from CDK outputs:

```bash
# Get cluster endpoint
CLUSTER_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name PMAgent-Database-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ClusterEndpoint`].OutputValue' \
  --output text \
  --region ap-southeast-2)

# Get secret ARN
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name PMAgent-Database-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`SecretArn`].OutputValue' \
  --output text \
  --region ap-southeast-2)

# Get credentials
DB_USER=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text | jq -r .username)
DB_PASS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text | jq -r .password)

# Export DATABASE_URL
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$CLUSTER_ENDPOINT:5432/pmgraph"

# Run migrations
make db:migrate
```

Verify tables were created:

```bash
psql $DATABASE_URL -c "\dt"
```

You should see: `task`, `node`, `edge`, `signal`, `audit`

## Step 10: Deploy WAF (Optional but Recommended)

```bash
aws cloudformation deploy \
  --template-file infra/cloudformation/apigw-waf.yaml \
  --stack-name PMAgent-WAF-dev \
  --parameter-overrides Environment=dev \
  --region ap-southeast-2
```

## Step 11: Smoke Test

```bash
# Run smoke test
make smoke
```

If plan_day Lambda doesn't exist yet (stub implementation), this will pass with a warning.

## Step 12: Enable Feature Flags Gradually

Edit `config/features.yaml` and enable one feature at a time:

```yaml
flags:
  send_emails: false
  create_calendar_holds: true     # Enable first
  create_planner_tasks: false
  jira_enabled: false
```

Test thoroughly before enabling the next feature.

## Step 13: Monitor Deployment

### CloudWatch Dashboard

Open the CloudWatch dashboard:

```bash
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name PMAgent-Observability-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardUrl`].OutputValue' \
  --output text \
  --region ap-southeast-2)

echo "Dashboard: $DASHBOARD_URL"
```

### Check Lambda Logs

```bash
# List recent log groups
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/PMAgent \
  --region ap-southeast-2

# Tail logs for a specific function
aws logs tail /aws/lambda/PMAgent-M365-mail_list_flagged --follow --region ap-southeast-2
```

### Verify Scheduled Rules

```bash
# Check EventBridge rules
aws events list-rules --region ap-southeast-2 | grep PMAgent
```

## Troubleshooting

### Lambda Can't Connect to Database

- Check Lambda is in correct VPC/subnets
- Verify security group allows traffic from VPC CIDR on port 5432
- Check VPC endpoints for Secrets Manager are working

### M365 Authentication Fails

- Verify client secret in Secrets Manager is correct
- Check API permissions are granted with admin consent
- Verify tenant ID and client ID in config/app.yaml

### EventBridge Not Triggering

- Check rule is enabled: `aws events describe-rule --name <rule-name>`
- Verify Lambda has resource-based policy allowing EventBridge
- Check CloudWatch Logs for Lambda errors

### High Costs

- Review CloudWatch dashboard for Bedrock token usage
- Check cost guards in config/app.yaml
- Disable non-critical EventBridge rules temporarily

## Post-Deployment

1. **Subscribe to Alarms**: Add email to SNS topic for CloudWatch alarms
2. **Review Security**: Run `make security` locally and fix any findings
3. **Test Flows**: Manually invoke plan_day, blocker_sweep, status_pack
4. **Document**: Update runbooks with any environment-specific details
5. **Backup**: Take Aurora snapshot before making schema changes

## Rollback

If deployment fails or causes issues:

```bash
# Rollback specific stack
cd infra/cdk
pnpm cdk rollback PMAgent-Lambdas-dev

# Or destroy all stacks (WARNING: loses data)
pnpm cdk destroy --all
```

**Note**: Database has `RemovalPolicy: SNAPSHOT`, so destroying creates final snapshot.

## Production Deployment

For production (`env: prod`):

1. Use separate AWS account or isolated VPC
2. Enable WAF with stricter rules
3. Set up cross-region replication for Aurora
4. Configure backup retention to 30 days
5. Enable AWS Shield Standard (automatic)
6. Set up CloudTrail for audit logs
7. Use AWS Secrets Manager rotation for secrets
8. Implement proper disaster recovery plan

## Support

For issues or questions:
- Check [Runbooks](ops/runbooks.md)
- Review CloudWatch Logs
- Open GitHub issue with logs and config (redact secrets!)

## Next Steps

After successful deployment:

1. Complete stub Lambda implementations (Planner, GitHub, etc.)
2. Implement AgentCore integration (currently placeholder)
3. Build out Next.js UI for web interface
4. Add comprehensive tests
5. Set up CI/CD pipeline for automated deployments
6. Document team onboarding and usage guides
