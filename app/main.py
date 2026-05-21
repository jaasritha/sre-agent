
from http.client import HTTPException
import logging
from fastapi import FastAPI
from app.webhook import router as webhook_router
from app.model import AlertEvent, WebhookResponse
from app.database import Base, engine
from app.model import AlertDB

# Create the database tables
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = FastAPI(
    title="SRE Ops agent",
    description="A simple SRE Ops agent to receive alerts and trigger actions",
    version="1.0.0"
)
app.include_router(webhook_router, tags=["Alerts"])

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "OK", "version": "1.0.0"}

@app.post('/webhook', response_model=WebhookResponse, tags=["Alerts"])
def receive_alert(alert: AlertEvent) -> WebhookResponse:
    logger.info(f"Received alert: {alert.alert_name} for service {alert.service}")

    if alert.severity not in ("critical", "warning", "info"):
        raise HTTPException(status_code=422, detail=f"Bad severity: {alert.severity}")

    return WebhookResponse(
        status="received",
        message="Alert accepted.",
        alert_name=alert.alert_name,
        severity=alert.severity,
    )