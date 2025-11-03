import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  kmsKey: kms.Key;
}

/**
 * Database Stack with Aurora Serverless v2 Postgres for work graph.
 */
export class DatabaseStack extends cdk.Stack {
  public readonly cluster: rds.DatabaseCluster;
  public readonly secret: rds.DatabaseSecret;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    // Database credentials secret
    this.secret = new rds.DatabaseSecret(this, 'DBSecret', {
      username: 'pmadmin',
      encryptionKey: props.kmsKey,
    });

    // Security group for database
    const dbSecurityGroup = new ec2.SecurityGroup(this, 'DBSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for PM Agent Aurora Postgres cluster',
      allowAllOutbound: false,
    });

    // Aurora Serverless v2 Cluster
    this.cluster = new rds.DatabaseCluster(this, 'PMAgentCluster', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_4,
      }),
      credentials: rds.Credentials.fromSecret(this.secret),
      writer: rds.ClusterInstance.serverlessV2('writer', {
        enablePerformanceInsights: true,
        performanceInsightEncryptionKey: props.kmsKey,
        performanceInsightRetention: rds.PerformanceInsightRetention.DEFAULT,
      }),
      readers: [
        rds.ClusterInstance.serverlessV2('reader1', {
          scaleWithWriter: true,
          enablePerformanceInsights: true,
          performanceInsightEncryptionKey: props.kmsKey,
        }),
      ],
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      securityGroups: [dbSecurityGroup],
      defaultDatabaseName: 'pmgraph',
      storageEncrypted: true,
      storageEncryptionKey: props.kmsKey,
      backup: {
        retention: cdk.Duration.days(7),
        preferredWindow: '03:00-04:00',
      },
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 2,
      removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
    });

    // Allow Lambda functions to connect
    dbSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(5432),
      'Allow Lambda access to Postgres'
    );

    // Outputs
    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: this.cluster.clusterEndpoint.hostname,
      description: 'Aurora cluster writer endpoint',
      exportName: 'PMAgentClusterEndpoint',
    });

    new cdk.CfnOutput(this, 'ClusterReadEndpoint', {
      value: this.cluster.clusterReadEndpoint.hostname,
      description: 'Aurora cluster reader endpoint',
    });

    new cdk.CfnOutput(this, 'SecretArn', {
      value: this.secret.secretArn,
      description: 'Database credentials secret ARN',
    });

    new cdk.CfnOutput(this, 'DatabaseName', {
      value: 'pmgraph',
      description: 'Default database name',
    });
  }
}
