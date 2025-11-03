import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';

export interface ObservabilityStackProps extends cdk.StackProps {}

/**
 * Observability Stack with CloudWatch dashboards and alarms.
 */
export class ObservabilityStack extends cdk.Stack {
  public readonly dashboard: cloudwatch.Dashboard;
  public readonly alarmTopic: sns.Topic;

  constructor(scope: Construct, id: string, props?: ObservabilityStackProps) {
    super(scope, id, props);

    // SNS Topic for alarms
    this.alarmTopic = new sns.Topic(this, 'PMAgentAlarms', {
      displayName: 'PM Agent Alarms',
      topicName: 'pm-agent-alarms',
    });

    // Add email subscription (update email after deployment)
    // this.alarmTopic.addSubscription(new subscriptions.EmailSubscription('ops@example.com'));

    // CloudWatch Dashboard
    this.dashboard = new cloudwatch.Dashboard(this, 'PMAgentDashboard', {
      dashboardName: 'PM-Agent-Operations',
      defaultInterval: cdk.Duration.hours(1),
    });

    // Lambda Metrics Widget
    const lambdaMetricsWidget = new cloudwatch.GraphWidget({
      title: 'Lambda Invocations & Errors',
      left: [
        new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'Invocations',
          statistic: 'Sum',
          label: 'Total Invocations',
        }),
      ],
      right: [
        new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'Errors',
          statistic: 'Sum',
          label: 'Errors',
          color: cloudwatch.Color.RED,
        }),
      ],
      width: 12,
    });

    // Lambda Duration Widget
    const lambdaDurationWidget = new cloudwatch.GraphWidget({
      title: 'Lambda Duration (p50, p95, p99)',
      left: [
        new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'Duration',
          statistic: 'p50',
          label: 'p50',
        }),
        new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'Duration',
          statistic: 'p95',
          label: 'p95',
          color: cloudwatch.Color.ORANGE,
        }),
        new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'Duration',
          statistic: 'p99',
          label: 'p99',
          color: cloudwatch.Color.RED,
        }),
      ],
      width: 12,
    });

    // Custom Metrics Widget (PMAgent namespace)
    const customMetricsWidget = new cloudwatch.GraphWidget({
      title: 'Tool Invocation Success/Failure',
      left: [
        new cloudwatch.Metric({
          namespace: 'PMAgent',
          metricName: 'ToolInvocationSuccess',
          statistic: 'Sum',
          label: 'Success',
          color: cloudwatch.Color.GREEN,
        }),
        new cloudwatch.Metric({
          namespace: 'PMAgent',
          metricName: 'ToolInvocationError',
          statistic: 'Sum',
          label: 'Errors',
          color: cloudwatch.Color.RED,
        }),
      ],
      width: 12,
    });

    // Database Metrics Widget
    const dbMetricsWidget = new cloudwatch.GraphWidget({
      title: 'Aurora Database Connections',
      left: [
        new cloudwatch.Metric({
          namespace: 'AWS/RDS',
          metricName: 'DatabaseConnections',
          statistic: 'Average',
          label: 'Active Connections',
        }),
      ],
      width: 12,
    });

    // Add widgets to dashboard
    this.dashboard.addWidgets(lambdaMetricsWidget, lambdaDurationWidget);
    this.dashboard.addWidgets(customMetricsWidget, dbMetricsWidget);

    // Alarm: Lambda Error Rate > 5%
    const lambdaErrorAlarm = new cloudwatch.Alarm(this, 'LambdaErrorRateAlarm', {
      metric: new cloudwatch.MathExpression({
        expression: 'errors / invocations * 100',
        usingMetrics: {
          errors: new cloudwatch.Metric({
            namespace: 'AWS/Lambda',
            metricName: 'Errors',
            statistic: 'Sum',
          }),
          invocations: new cloudwatch.Metric({
            namespace: 'AWS/Lambda',
            metricName: 'Invocations',
            statistic: 'Sum',
          }),
        },
      }),
      threshold: 5,
      evaluationPeriods: 2,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Lambda error rate exceeds 5%',
      alarmName: 'PMAgent-Lambda-HighErrorRate',
    });

    lambdaErrorAlarm.addAlarmAction({
      bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
    });

    // Alarm: Database Connection Saturation
    const dbConnectionAlarm = new cloudwatch.Alarm(this, 'DBConnectionAlarm', {
      metric: new cloudwatch.Metric({
        namespace: 'AWS/RDS',
        metricName: 'DatabaseConnections',
        statistic: 'Average',
      }),
      threshold: 80,
      evaluationPeriods: 3,
      alarmDescription: 'Database connections approaching limit',
      alarmName: 'PMAgent-DB-HighConnections',
    });

    dbConnectionAlarm.addAlarmAction({
      bind: () => ({ alarmActionArn: this.alarmTopic.topicArn }),
    });

    // Outputs
    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${this.dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL',
    });

    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: this.alarmTopic.topicArn,
      description: 'SNS Topic ARN for alarms',
    });
  }
}
