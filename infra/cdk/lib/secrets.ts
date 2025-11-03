import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface SecretsStackProps extends cdk.StackProps {
  kmsKey: kms.Key;
}

/**
 * Secrets Stack with placeholder secrets for PM Agent.
 * Update values after deployment via AWS Console or CLI.
 */
export class SecretsStack extends cdk.Stack {
  public readonly m365ClientSecret: secretsmanager.Secret;
  public readonly githubToken: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: SecretsStackProps) {
    super(scope, id, props);

    // M365 Client Secret (placeholder - update after deploy)
    this.m365ClientSecret = new secretsmanager.Secret(this, 'M365ClientSecret', {
      secretName: '/pm-agent/m365/client-secret',
      description: 'Microsoft 365 client secret for Graph API authentication',
      encryptionKey: props.kmsKey,
      secretStringValue: cdk.SecretValue.unsafePlainText('PLACEHOLDER-UPDATE-AFTER-DEPLOY'),
    });

    // GitHub Token (placeholder)
    this.githubToken = new secretsmanager.Secret(this, 'GitHubToken', {
      secretName: '/pm-agent/github/token',
      description: 'GitHub personal access token',
      encryptionKey: props.kmsKey,
      secretStringValue: cdk.SecretValue.unsafePlainText('PLACEHOLDER-UPDATE-AFTER-DEPLOY'),
    });

    // Outputs with warning
    new cdk.CfnOutput(this, 'M365SecretName', {
      value: this.m365ClientSecret.secretName,
      description: 'M365 client secret name (UPDATE VALUE AFTER DEPLOY)',
    });

    new cdk.CfnOutput(this, 'GitHubSecretName', {
      value: this.githubToken.secretName,
      description: 'GitHub token secret name (UPDATE VALUE AFTER DEPLOY)',
    });
  }
}
