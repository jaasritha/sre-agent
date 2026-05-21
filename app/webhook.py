import logging
from fastapi import APIRouter, HTTPException, status
from app.model import AlertEvent, WebhookResponse, AlertDB
import json
from app.database import SessionLocal
logger = logging.getLogger(__name__)
router = APIRouter()

# analyzer 
from app.analyzer import analyze_alert
from app.notifier import send_slack_alert 


@router.post("/webhook", response_model=WebhookResponse, status_code=status.HTTP_200_OK)
async def receive_webhook(alert: AlertEvent) -> WebhookResponse:
    logger.info(f"Received alert: {alert.alert_name} for service {alert.service}")
    
    # excepton handling for invalid severity
    if alert.severity not in ("critical", "warning", "info"):
        raise HTTPException(status_code=422, detail=f"Bad severity: {alert.severity}")  
    # Here you can add logic to process the alert, e.g., store it in a database, trigger actions, etc.
    db = SessionLocal()
    try:
        alert_db = AlertDB(
            alert_id=alert.alert_id,
            alert_name=alert.alert_name,
            service=alert.service,
            severity=alert.severity,
            labels=json.dumps(alert.labels),
            fired_at=alert.fired_at
        )
        db.add(alert_db)
        db.commit()
        analysis_result = analyze_alert(alert)
        alert_db.analysis = analysis_result
        db.commit()
        db.refresh(alert_db)
    finally:
        db.close()
    notified = send_slack_alert(alert, analysis_result) # 1
    logger.info("Slack notified: %s", notified)  # 2
    return WebhookResponse.fake_handler(alert)