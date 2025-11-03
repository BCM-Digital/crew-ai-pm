import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface SecurityStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

/**
 * Security Stack with IAM roles (least privilege) and KMS key.
 */
export class SecurityStack extends cdk.Stack {
  public readonly kmsKey: kms.Key;
  public readonly m365Role: iam.Role;
  public readonly githubRole: iam.Role;
  public readonly jiraRole: iam.Role;
  public readonly devopsRole: iam.Role;

  constructor(scope: Construct, id: string, props: SecurityStackProps) {
    super(scope, id, props);

    // KMS Key for encryption
    this.kmsKey = new kms.Key(this, 'PMAgentKMSKey', {
      description: 'KMS key for PM Agent secrets and data encryption',
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // M365 Tool Role
    this.m365Role = new iam.Role(this, 'M365ToolRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for M365 tool adapter Lambdas',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    // Grant SSM Parameter Store read for M365 secrets
    this.m365Role.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter', 'ssm:GetParameters'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/pm-agent/m365/*`,
        ],
      })
    );

    // Grant KMS decrypt
    this.kmsKey.grantDecrypt(this.m365Role);

    // GitHub Tool Role
    this.githubRole = new iam.Role(this, 'GitHubToolRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for GitHub tool adapter Lambdas',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    this.githubRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/pm-agent/github/*`,
        ],
      })
    );

    this.kmsKey.grantDecrypt(this.githubRole);

    // Jira Tool Role
    this.jiraRole = new iam.Role(this, 'JiraToolRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for Jira tool adapter Lambdas',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    this.jiraRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/pm-agent/jira/*`,
        ],
      })
    );

    this.kmsKey.grantDecrypt(this.jiraRole);

    // DevOps Tool Role (read-only for Octopus, Vercel, ECS)
    this.devopsRole = new iam.Role(this, 'DevOpsToolRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for DevOps tool adapter Lambdas (read-only)',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    this.devopsRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/pm-agent/devops/*`,
        ],
      })
    );

    // Grant ECS read-only access
    this.devopsRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ecs:DescribeServices',
          'ecs:DescribeTasks',
          'ecs:DescribeClusters',
          'ecs:ListServices',
        ],
        resources: ['*'],
      })
    );

    this.kmsKey.grantDecrypt(this.devopsRole);

    // Outputs
    new cdk.CfnOutput(this, 'KMSKeyId', {
      value: this.kmsKey.keyId,
      description: 'KMS Key ID for PM Agent',
      exportName: 'PMAgentKMSKeyId',
    });

    new cdk.CfnOutput(this, 'M365RoleArn', {
      value: this.m365Role.roleArn,
      description: 'M365 Tool Lambda Role ARN',
    });
  }
}
