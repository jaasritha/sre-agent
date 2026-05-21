import os
import logging
from slack_sdk.webhook import WebhookClient               # 1
from dotenv import load_dotenv
from app.model import AlertEvent

load_dotenv()
logger = logging.getLogger(__name__)

SEVERITY_COLOURS = {                                       # 2
    "critical": "#E01E5A",
    "warning":  "#ECB22E",
    "info":     "#36C5F0",
}


def _get_client() -> WebhookClient | None:                 # 3
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        logger.warning("SLACK_WEBHOOK_URL not set — skipping Slack")
        return None
    return WebhookClient(url)


def _build_blocks(                                         # 4
    alert: AlertEvent,
    analysis: str,
) -> list[dict]:
    severity  = alert.severity.upper()
    labels_str = ", ".join(f"{k}={v}" for k, v in alert.labels.items()) or "none"
    analysis_preview = analysis[:300] + "..." \
        if len(analysis) > 300 else analysis              # 5

    return [
        {
            "type": "section",                             # 6
            "text": {
                "type": "mrkdwn",
                "text": f"*[{severity}] {alert.alert_name}* — `{alert.service}`",
            },
        },
        {"type": "divider"},
        {
            "type": "section",                             # 7
            "fields": [
                {"type": "mrkdwn", "text": f"*Service*\n{alert.service}"},
                {"type": "mrkdwn", "text": f"*Severity*\n{severity}"},
                {"type": "mrkdwn", "text": f"*Labels*\n{labels_str}"},
                {"type": "mrkdwn", "text": f"*Alert ID*\n`{alert.alert_id[:8]}...`"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",                             # 8
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Analysis*\n{analysis_preview}",
            },
        },
    ]


def send_slack_alert(                                      # 9
    alert: AlertEvent,
    analysis: str,
) -> bool:
    client = _get_client()
    if client is None:
        return False

    colour = SEVERITY_COLOURS.get(alert.severity, "#888888")

    try:
        resp = client.send(                                # 10
            text=f"Alert: {alert.alert_name} on {alert.service}",
            attachments=[{                                 # 11
                "color": colour,
                "blocks": _build_blocks(alert, analysis),
            }],
        )
        if resp.status_code == 200:
            logger.info("Slack notified for %s", alert.alert_name)
            return True
        logger.warning("Slack returned %d", resp.status_code)
        return False

    except Exception as e:                                 # 12
        logger.error("Slack notification failed: %s", e)
        return False