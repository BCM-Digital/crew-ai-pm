# PM Agent Operational Runbooks

## Table of Contents

- [Emergency Response](#emergency-response)
- [Common Issues](#common-issues)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Monitoring](#monitoring)

## Emergency Response

### High Error Rate Alert

**Symptom**: CloudWatch alarm fires for Lambda error rate > 5%

**Steps**:
1. Check CloudWatch dashboard for specific Lambda functions with errors
2. View CloudWatch Logs Insights:
   ```
   fields @timestamp, @message, error_code, tool, trace_id
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 50
   ```
3. Identify common error patterns (auth_error, rate_limited, internal)
4. If auth_error: Verify secrets in Secrets Manager are valid
5. If rate_limited: Check M365/GitHub rate limit status, adjust schedules if needed
6. If internal: Check database connection pool, Aurora cluster status

**Escalation**: If errors persist > 30 minutes, page on-call engineer

### Database Connection Saturation

**Symptom**: CloudWatch alarm for DatabaseConnections > 80

**Steps**:
1. Check active Lambda concurrency:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name ConcurrentExecutions \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Maximum
   ```
2. Review Aurora Serverless scaling: Check if cluster is at max capacity (2 ACUs)
3. If at max capacity, consider increasing `serverlessV2MaxCapacity` in CDK
4. Check for long-running queries:
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY duration DESC
   LIMIT 10;
   ```
5. Terminate blocking queries if safe to do so

### Approval Token Failures

**Symptom**: Repeated auth_error on approval-required tools

**Cause**: Approval tokens expired, payload mismatch, or single-use token replayed

**Steps**:
1. Check CloudWatch Logs for approval token validation failures
2. Look for `action_hash` mismatches - indicates payload changed after approval
3. Check token TTL configuration in `config/app.yaml` (default 10 minutes)
4. Verify approval flow:
   - Card posted to Teams
   - User clicked Approve within TTL
   - Payload hasn't changed between approval request and execution
5. If payload mismatch is common, review AgentCore prompt for consistency

### Cost Spike

**Symptom**: AWS Cost Explorer shows unexpected Bedrock or Lambda costs

**Steps**:
1. Check token usage in CloudWatch Metrics:
   ```
   Namespace: PMAgent
   Metric: BedrockTokensUsed
   ```
2. Review cost guard limits in `config/app.yaml`:
   - `max_bedrock_tokens_per_run`: 200,000
   - `max_tool_invocations_per_run`: 200
   - `monthly_stop_after_tokens`: 20,000,000
3. Check if monthly kill switch has been triggered
4. Identify runaway flows or prompts generating excessive tokens
5. Adjust schedules or disable non-critical flows temporarily

## Common Issues

### Emails Not Being Drafted

**Cause**: Feature flag disabled or approval token missing

**Check**:
1. `config/features.yaml`: Ensure `send_emails: true` (or false for testing)
2. Verify M365 Graph permissions include `Mail.Send`
3. Check Lambda logs for approval token validation
4. Verify Teams DM chat ID is correct in SSM Parameter Store

### Calendar Holds Not Created

**Cause**: Feature flag disabled or incorrect calendar permissions

**Check**:
1. `config/features.yaml`: Ensure `create_calendar_holds: true`
2. Verify M365 Graph permissions include `Calendars.ReadWrite`
3. Check for timezone issues - holds should be in Brisbane time
4. Review Lambda logs for Graph API errors

### Planner Tasks Not Created

**Note**: Planner integration is stub implementation, requires completion

**Check**:
1. `config/features.yaml`: Ensure `create_planner_tasks: true`
2. Verify plan names in `config/projects.yaml` match actual Planner plans
3. Check M365 Graph permissions include `Tasks.ReadWrite` and `Sites.ReadWrite.All`
4. Review Lambda logs for Graph API plan/bucket lookup errors

### Database Connection Refused

**Cause**: Lambda not in correct VPC/subnets or security group misconfiguration

**Steps**:
1. Verify Lambda is in `PRIVATE_ISOLATED` subnets
2. Check Aurora security group allows inbound from VPC CIDR on port 5432
3. Verify VPC endpoints for Secrets Manager and SSM are working
4. Test connection from Lambda:
   ```python
   import psycopg2
   conn = psycopg2.connect(os.environ['DATABASE_URL'])
   ```

## Troubleshooting

### Debugging Approval Tokens

1. Enable verbose logging in approval validation (common.py)
2. Check token claims (if JWT implemented):
   ```bash
   echo "TOKEN" | cut -d. -f2 | base64 -d | jq
   ```
3. Verify action hash matches:
   ```python
   import hashlib, json
   payload = {"to": [...], "subject": "...", "body": "..."}
   hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
   ```
4. Check token TTL hasn't expired
5. Verify token hasn't been used before (single-use check)

### Investigating Tool Invocation Failures

1. Find trace_id from Teams card or CloudWatch
2. Query CloudWatch Logs Insights:
   ```
   fields @timestamp, tool, ok, error_code, latency_ms
   | filter trace_id = "abc123"
   | sort @timestamp
   ```
3. Check audit table for full history:
   ```sql
   SELECT * FROM audit WHERE run_id = 'abc123' ORDER BY at;
   ```
4. Review error_code mapping (common.py):
   - `bad_args`: Input validation failed
   - `not_found`: Resource doesn't exist
   - `rate_limited`: Vendor rate limit hit
   - `auth_error`: Authentication/authorisation failed
   - `conflict`: Resource conflict (e.g., duplicate)
   - `internal`: Server error or timeout

### Analysing Flow Performance

1. Check p95/p99 latency by tool:
   ```
   fields tool, latency_ms
   | stats avg(latency_ms), percentile(latency_ms, 95), percentile(latency_ms, 99) by tool
   ```
2. Identify slow tools and optimise:
   - Add caching for read-heavy tools
   - Batch requests where possible
   - Increase Lambda memory if CPU-bound
3. Review retry policy - excessive retries can indicate systemic issue

## Maintenance

### Database Migrations

**When**: Adding new columns, tables, or indexes

**Steps**:
1. Create migration SQL in `runtime/db/sql/00X_migration_name.sql`
2. Test locally or in dev environment first
3. Run migration:
   ```bash
   export DATABASE_URL="postgresql://..."
   psql $DATABASE_URL -f runtime/db/sql/00X_migration_name.sql
   ```
4. Verify with smoke tests
5. Document in runbook if rollback may be needed

### Rotating Secrets

**When**: Quarterly or after suspected compromise

**M365 Client Secret**:
1. Generate new client secret in Azure Portal
2. Update Secrets Manager:
   ```bash
   aws secretsmanager update-secret \
     --secret-id /pm-agent/m365/client-secret \
     --secret-string "NEW_SECRET"
   ```
3. Verify tools still work (check CloudWatch logs)
4. Delete old secret from Azure Portal after 24 hours

**GitHub Token**:
1. Generate new PAT in GitHub Settings
2. Update Secrets Manager:
   ```bash
   aws secretsmanager update-secret \
     --secret-id /pm-agent/github/token \
     --secret-string "NEW_TOKEN"
   ```
3. Verify GitHub tools work

### Scaling Database

**When**: Consistent high connection count or slow queries

**Steps**:
1. Review Aurora Performance Insights
2. Identify slow queries and add indexes
3. If needed, increase `serverlessV2MaxCapacity`:
   ```typescript
   // In db-postgres.ts
   serverlessV2MaxCapacity: 4,  // was 2
   ```
4. Deploy CDK stack
5. Monitor costs after scaling

## Monitoring

### Key Metrics

- **Lambda Error Rate**: < 1% (alarm at 5%)
- **Lambda p95 Duration**: < 5s for tool adapters, < 30s for flows
- **Database Connections**: < 80 (alarm at 80)
- **Tool Success Rate**: > 95% per tool
- **Bedrock Token Usage**: < 200k per run, < 20M per month

### Dashboard Views

**Operations Dashboard** (`PMAgent-Operations`):
- Lambda invocations and errors
- Lambda duration percentiles
- Tool success/failure counts
- Database connections

**Cost Dashboard** (create manually):
- Bedrock token usage
- Lambda invocation count
- RDS ACU hours
- Data transfer costs

### Log Queries

**Recent Errors**:
```
fields @timestamp, @message, tool, error_code, trace_id
| filter level = "ERROR"
| sort @timestamp desc
| limit 100
```

**Tool Performance**:
```
fields tool, latency_ms, ok
| stats avg(latency_ms) as avg_latency, count(*) as invocations by tool, ok
| sort avg_latency desc
```

**Approval Token Failures**:
```
fields @timestamp, tool, action_hash
| filter @message like /Invalid approval token/
| count() by tool
```

## Support Contacts

- **Platform Team**: platform-team@example.com
- **On-Call**: oncall@example.com
- **AWS Support**: [Support Centre](https://console.aws.amazon.com/support/)
- **Microsoft Support**: For M365 Graph API issues

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2024-02-01 | Initial runbook | Platform Team |
