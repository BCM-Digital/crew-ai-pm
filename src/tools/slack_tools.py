"""Slack tools for PM Agent system."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..config import settings
from ..schemas import SlackMessageParams, SlackApprovalParams


def send_message(
    channel: str,
    text: str,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None
) -> Dict[str, Any]:
    """Send a message to a Slack channel."""
    try:
        client = WebClient(token=settings.slack_bot_token)
        
        response = client.chat_postMessage(
            channel=channel.lstrip('#'),
            text=text,
            blocks=blocks,
            thread_ts=thread_ts
        )
        
        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"],
            "text": text
        }
        
    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}",
            "details": f"Failed to send message to {channel}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to send Slack message to {channel}"
        }


def send_approval_request(
    channel: str,
    title: str,
    description: str,
    action_data: Dict[str, Any],
    requester: str
) -> Dict[str, Any]:
    """Send an approval request to Slack with interactive buttons."""
    try:
        client = WebClient(token=settings.slack_bot_token)
        
        # Format approval blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Approval Required: {title}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Requested by:* {requester} | *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Action Details:*\n```{str(action_data)}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "style": "primary",
                        "action_id": "approve_action",
                        "value": str(action_data)
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject"
                        },
                        "style": "danger",
                        "action_id": "reject_action",
                        "value": str(action_data)
                    }
                ]
            }
        ]
        
        response = client.chat_postMessage(
            channel=channel.lstrip('#'),
            text=f"Approval Required: {title}",
            blocks=blocks
        )
        
        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"],
            "approval_id": f"{response['channel']}_{response['ts']}",
            "title": title,
            "status": "pending"
        }
        
    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}",
            "details": f"Failed to send approval request to {channel}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to send approval request to {channel}"
        }


def post_daily_standup(
    channel: str,
    date: str,
    completed_yesterday: List[str],
    planned_today: List[str],
    blockers: List[str],
    sprint_progress: Dict[str, Any]
) -> Dict[str, Any]:
    """Post a formatted daily standup report to Slack."""
    try:
        client = WebClient(token=settings.slack_bot_token)
        
        # Format standup blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Daily Standup - {date}"
                }
            }
        ]
        
        # Completed yesterday section
        if completed_yesterday:
            completed_text = "\n".join([f"• {item}" for item in completed_yesterday])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ Completed Yesterday:*\n{completed_text}"
                }
            })
        
        # Planned today section
        if planned_today:
            planned_text = "\n".join([f"• {item}" for item in planned_today])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎯 Planned Today:*\n{planned_text}"
                }
            })
        
        # Blockers section
        if blockers:
            blockers_text = "\n".join([f"• {blocker}" for blocker in blockers])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚫 Blockers:*\n{blockers_text}"
                }
            })
        
        # Sprint progress section
        if sprint_progress:
            progress_text = f"*Sprint Progress:* {sprint_progress.get('completed', 0)}/{sprint_progress.get('total', 0)} stories"
            if 'velocity' in sprint_progress:
                progress_text += f" | *Velocity:* {sprint_progress['velocity']} pts"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": progress_text
                }
            })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        response = client.chat_postMessage(
            channel=channel.lstrip('#'),
            text=f"Daily Standup - {date}",
            blocks=blocks
        )
        
        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"],
            "standup_date": date,
            "blocks_count": len(blocks)
        }
        
    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}",
            "details": f"Failed to post standup to {channel}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to post daily standup to {channel}"
        }


def post_sprint_report(
    channel: str,
    sprint_name: str,
    sprint_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Post a comprehensive sprint report to Slack.
    
    Args:
        channel: Slack channel for the report
        sprint_name: Name of the completed sprint
        sprint_summary: Sprint metrics and summary data
    
    Returns:
        Dictionary with sprint report status
    """
    try:
        client = WebClient(token=settings.slack_bot_token)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🏃‍♂️ Sprint Report: {sprint_name}"
                }
            }
        ]
        
        # Sprint metrics
        metrics = sprint_summary.get('metrics', {})
        if metrics:
            metrics_text = ""
            if 'completed_stories' in metrics:
                metrics_text += f"*Completed Stories:* {metrics['completed_stories']}\n"
            if 'story_points' in metrics:
                metrics_text += f"*Story Points:* {metrics['story_points']}\n"
            if 'velocity' in metrics:
                metrics_text += f"*Team Velocity:* {metrics['velocity']}\n"
            if 'completion_rate' in metrics:
                metrics_text += f"*Completion Rate:* {metrics['completion_rate']}%\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": metrics_text.strip()
                }
            })
        
        # Completed work
        completed = sprint_summary.get('completed', [])
        if completed:
            completed_text = "\n".join([f"• {item}" for item in completed[:10]])
            if len(completed) > 10:
                completed_text += f"\n... and {len(completed) - 10} more"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ Completed Work:*\n{completed_text}"
                }
            })
        
        # Incomplete work
        incomplete = sprint_summary.get('incomplete', [])
        if incomplete:
            incomplete_text = "\n".join([f"• {item}" for item in incomplete])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⏳ Incomplete Work:*\n{incomplete_text}"
                }
            })
        
        # Retrospective notes
        retro_notes = sprint_summary.get('retrospective', [])
        if retro_notes:
            retro_text = "\n".join([f"• {note}" for note in retro_notes])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔍 Retrospective Notes:*\n{retro_text}"
                }
            })
        
        response = client.chat_postMessage(
            channel=channel.lstrip('#'),
            text=f"Sprint Report: {sprint_name}",
            blocks=blocks
        )
        
        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"],
            "sprint_name": sprint_name,
            "report_sections": len(blocks)
        }
        
    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}",
            "details": f"Failed to post sprint report to {channel}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to post sprint report to {channel}"
        }


def notify_risk_flags(
    channel: str,
    risk_flags: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Send risk flag notifications to Slack.
    
    Args:
        channel: Slack channel for notifications
        risk_flags: List of risk flags to notify about
    
    Returns:
        Dictionary with notification status
    """
    try:
        if not risk_flags:
            return {
                "success": True,
                "message": "No risk flags to notify about",
                "flags_count": 0
            }
        
        client = WebClient(token=settings.slack_bot_token)
        
        # Group risk flags by severity
        high_severity = [rf for rf in risk_flags if rf.get('severity') == 'high']
        medium_severity = [rf for rf in risk_flags if rf.get('severity') == 'medium']
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ Risk Flags Detected ({len(risk_flags)} total)"
                }
            }
        ]
        
        # High severity flags
        if high_severity:
            high_text = ""
            for flag in high_severity[:5]:  # Limit to 5 per severity
                high_text += f"• *{flag.get('type', 'Unknown')}*: {flag.get('description', 'No description')}\n"
                if flag.get('source_url'):
                    high_text += f"  <{flag['source_url']}|View Source>\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔴 High Severity ({len(high_severity)}):*\n{high_text.strip()}"
                }
            })
        
        # Medium severity flags
        if medium_severity:
            medium_text = ""
            for flag in medium_severity[:5]:  # Limit to 5 per severity
                medium_text += f"• *{flag.get('type', 'Unknown')}*: {flag.get('description', 'No description')}\n"
                if flag.get('source_url'):
                    medium_text += f"  <{flag['source_url']}|View Source>\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🟡 Medium Severity ({len(medium_severity)}):*\n{medium_text.strip()}"
                }
            })
        
        response = client.chat_postMessage(
            channel=channel.lstrip('#'),
            text=f"Risk Flags Detected: {len(risk_flags)} total",
            blocks=blocks
        )
        
        return {
            "success": True,
            "message_ts": response["ts"],
            "channel": response["channel"],
            "flags_notified": len(risk_flags),
            "high_severity_count": len(high_severity),
            "medium_severity_count": len(medium_severity)
        }
        
    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}",
            "details": f"Failed to send risk flag notifications to {channel}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"Failed to send risk flag notifications to {channel}"
        } 