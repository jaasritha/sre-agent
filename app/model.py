from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy import String, Text, DateTime  # 1
from sqlalchemy.orm import mapped_column, Mapped
import json
from app.database import Base

class AlertEvent(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_name: str
    service: str
    severity: str
    labels: dict = Field (default_factory=dict)
    fired_at: Optional[datetime] = Field (default_factory=datetime.utcnow)


alert = AlertEvent(
    alert_id="12345",
    alert_name="High CPU Usage",
    service="web-server",
    severity="critical"
)


class WebhookResponse(BaseModel):
    status: str
    message: Optional[str] = None
    alert_name: Optional[str] = None
    serverity: Optional[str] = None

    def fake_handler(alert: AlertEvent) -> "WebhookResponse":
        return WebhookResponse(
            status="success",
            message=f"Received alert {alert.alert_name} for service {alert.service}",
            alert_name=alert.alert_name,
            serverity=alert.severity
        )

class AlertDB(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(unique=True, index=True)
    alert_name: Mapped[str] = mapped_column()
    service: Mapped[str] = mapped_column()
    severity: Mapped[str] = mapped_column()
    labels: Mapped[str] = mapped_column()
    fired_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    def set_labels(self, labels: dict):
        self.labels = json.dumps(labels)
    def get_labels(self) -> dict:
        return json.loads(self.labels) if self.labels else {}