import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as path from 'path';

export interface LambdasStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  databaseCluster: rds.DatabaseCluster;
  m365Role: iam.Role;
  githubRole: iam.Role;
}

/**
 * Lambdas Stack defining all tool adapter Lambda functions.
 */
export class LambdasStack extends cdk.Stack {
  public readonly m365Functions: Record<string, lambda.Function>;
  public readonly githubFunctions: Record<string, lambda.Function>;

  constructor(scope: Construct, id: string, props: LambdasStackProps) {
    super(scope, id, props);

    // Common Lambda environment variables
    const commonEnv = {
      AWS_REGION: this.region,
      LOG_LEVEL: 'INFO',
      POWERTOOLS_SERVICE_NAME: 'pm-agent',
      POWERTOOLS_METRICS_NAMESPACE: 'PMAgent',
    };

    // M365 environment variables
    const m365Env = {
      ...commonEnv,
      M365_TENANT_ID: 'TBD',
      M365_CLIENT_ID: 'TBD',
      M365_CLIENT_SECRET_SSM: '/pm-agent/m365/client-secret',
    };

    // Lambda layer for dependencies (would be built separately)
    const powerToolsLayer = lambda.LayerVersion.fromLayerVersionArn(
      this,
      'PowerToolsLayer',
      `arn:aws:lambda:${this.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:59`
    );

    // M365 Lambda Functions
    this.m365Functions = {};

    const m365Tools = [
      'mail_list_flagged',
      'mail_draft',
      'calendar_list',
      'calendar_hold',
      'planner_create',
      'teams_send_card',
    ];

    m365Tools.forEach((tool) => {
      this.m365Functions[tool] = new lambda.Function(this, `M365-${tool}`, {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: `${tool}.handler`,
        code: lambda.Code.fromAsset(path.join(__dirname, '../../../lambdas/m365')),
        role: props.m365Role,
        vpc: props.vpc,
        vpcSubnets: {
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
        environment: m365Env,
        timeout: cdk.Duration.seconds(30),
        memorySize: 512,
        layers: [powerToolsLayer],
        tracing: lambda.Tracing.ACTIVE,
        description: `M365 tool adapter: ${tool}`,
      });

      // Grant database access
      props.databaseCluster.grantConnect(this.m365Functions[tool]);
    });

    // GitHub Lambda Functions
    this.githubFunctions = {};

    const githubTools = ['pr_list', 'issue_create'];

    githubTools.forEach((tool) => {
      this.githubFunctions[tool] = new lambda.Function(this, `GitHub-${tool}`, {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: `${tool}.handler`,
        code: lambda.Code.fromAsset(path.join(__dirname, '../../../lambdas/github')),
        role: props.githubRole,
        vpc: props.vpc,
        vpcSubnets: {
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
        environment: {
          ...commonEnv,
          GITHUB_TOKEN_SSM: '/pm-agent/github/token',
        },
        timeout: cdk.Duration.seconds(30),
        memorySize: 256,
        layers: [powerToolsLayer],
        tracing: lambda.Tracing.ACTIVE,
        description: `GitHub tool adapter: ${tool}`,
      });

      props.databaseCluster.grantConnect(this.githubFunctions[tool]);
    });

    // Outputs
    new cdk.CfnOutput(this, 'M365MailListFunctionArn', {
      value: this.m365Functions['mail_list_flagged'].functionArn,
      description: 'M365 Mail List Flagged Lambda ARN',
    });

    new cdk.CfnOutput(this, 'M365MailDraftFunctionArn', {
      value: this.m365Functions['mail_draft'].functionArn,
      description: 'M365 Mail Draft Lambda ARN',
    });
  }
}
