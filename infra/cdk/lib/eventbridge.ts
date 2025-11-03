import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface EventBridgeStackProps extends cdk.StackProps {}

/**
 * EventBridge Stack with scheduled rules for PM Agent flows.
 * Schedules are in Brisbane timezone (AEST/AEDT).
 */
export class EventBridgeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: EventBridgeStackProps) {
    super(scope, id, props);

    // Plan Day Rule - 07:30 Brisbane time (21:30 UTC during AEST, 20:30 UTC during AEDT)
    // Using cron(30 21 * * ? *) for AEST approximation
    const planDayRule = new events.Rule(this, 'PlanDayRule', {
      schedule: events.Schedule.cron({
        minute: '30',
        hour: '21', // 07:30 Brisbane AEST = 21:30 UTC
        weekDay: 'MON-FRI',
      }),
      description: 'Trigger Plan Day flow at 07:30 Brisbane time on weekdays',
      enabled: true,
    });

    // Blocker Sweep Rule - Every 2 hours during work hours
    const blockerSweepRule = new events.Rule(this, 'BlockerSweepRule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(2)),
      description: 'Trigger Blocker Sweep flow every 2 hours',
      enabled: true,
    });

    // Status Pack Rule - 15:30 Brisbane time (05:30 UTC during AEST)
    const statusPackRule = new events.Rule(this, 'StatusPackRule', {
      schedule: events.Schedule.cron({
        minute: '30',
        hour: '5', // 15:30 Brisbane AEST = 05:30 UTC
        weekDay: 'MON-FRI',
      }),
      description: 'Trigger Status Pack flow at 15:30 Brisbane time on weekdays',
      enabled: true,
    });

    // Note: Lambda targets would be added here once flow Lambdas are created
    // Example:
    // planDayRule.addTarget(new targets.LambdaFunction(planDayLambda));

    // Outputs
    new cdk.CfnOutput(this, 'PlanDayRuleArn', {
      value: planDayRule.ruleArn,
      description: 'Plan Day EventBridge rule ARN',
    });

    new cdk.CfnOutput(this, 'BlockerSweepRuleArn', {
      value: blockerSweepRule.ruleArn,
      description: 'Blocker Sweep EventBridge rule ARN',
    });

    new cdk.CfnOutput(this, 'StatusPackRuleArn', {
      value: statusPackRule.ruleArn,
      description: 'Status Pack EventBridge rule ARN',
    });
  }
}
