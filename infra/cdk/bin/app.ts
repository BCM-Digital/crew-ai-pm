#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcStack } from '../lib/vpc';
import { SecurityStack } from '../lib/security';
import { SecretsStack } from '../lib/secrets';
import { DatabaseStack } from '../lib/db-postgres';
import { LambdasStack } from '../lib/lambdas';
import { EventBridgeStack } from '../lib/eventbridge';
import { ObservabilityStack } from '../lib/observability';
import { AwsSolutionsChecks } from 'cdk-nag';
import { Aspects } from 'aws-cdk-lib';

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'ap-southeast-2',
};

const envName = process.env.ENV || 'dev';

// Common tags
const tags = {
  app: 'pm-agent',
  env: envName,
  owner: 'platform-team',
  'cost-centre': 'engineering',
  managedBy: 'cdk',
};

// VPC Stack - Foundation networking
const vpcStack = new VpcStack(app, `PMAgent-VPC-${envName}`, {
  env,
  description: 'VPC with S3 and DynamoDB gateway endpoints for PM Agent',
});

// Security Stack - IAM roles, KMS keys
const securityStack = new SecurityStack(app, `PMAgent-Security-${envName}`, {
  env,
  vpc: vpcStack.vpc,
  description: 'Security resources (IAM, KMS) for PM Agent',
});

// Secrets Stack - Secrets Manager resources
const secretsStack = new SecretsStack(app, `PMAgent-Secrets-${envName}`, {
  env,
  kmsKey: securityStack.kmsKey,
  description: 'Secrets Manager resources for PM Agent',
});

// Database Stack - Aurora Serverless v2 Postgres
const databaseStack = new DatabaseStack(app, `PMAgent-Database-${envName}`, {
  env,
  vpc: vpcStack.vpc,
  kmsKey: securityStack.kmsKey,
  description: 'Aurora Serverless v2 Postgres database for PM Agent work graph',
});

// Lambdas Stack - Tool adapter Lambda functions
const lambdasStack = new LambdasStack(app, `PMAgent-Lambdas-${envName}`, {
  env,
  vpc: vpcStack.vpc,
  databaseCluster: databaseStack.cluster,
  m365Role: securityStack.m365Role,
  githubRole: securityStack.githubRole,
  description: 'Lambda functions for PM Agent tool adapters',
});

// EventBridge Stack - Scheduled flows
const eventBridgeStack = new EventBridgeStack(app, `PMAgent-EventBridge-${envName}`, {
  env,
  description: 'EventBridge rules for PM Agent scheduled flows',
});

// Observability Stack - CloudWatch dashboards and alarms
const observabilityStack = new ObservabilityStack(app, `PMAgent-Observability-${envName}`, {
  env,
  description: 'CloudWatch dashboards and alarms for PM Agent',
});

// Apply tags to all stacks
Object.entries(tags).forEach(([key, value]) => {
  cdk.Tags.of(vpcStack).add(key, value);
  cdk.Tags.of(securityStack).add(key, value);
  cdk.Tags.of(secretsStack).add(key, value);
  cdk.Tags.of(databaseStack).add(key, value);
  cdk.Tags.of(lambdasStack).add(key, value);
  cdk.Tags.of(eventBridgeStack).add(key, value);
  cdk.Tags.of(observabilityStack).add(key, value);
});

// Apply cdk-nag checks for security compliance
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

app.synth();
