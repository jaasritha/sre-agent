from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


VALID_ALERT = {
    "alert_name": "High CPU Usage",
    "service": "web-server",
    "severity": "critical",
    "labels": {"env": "production"}
    }

def test_valid_alert_returns_200():
    response = client.post("/webhook", json=VALID_ALERT)
    assert response.status_code == 200

def test_response_has_status_received():
    response = client.post("/webhook", json=VALID_ALERT)
    assert response.json().get("status") == "success"

def test_bad_severity_returns_422():
    invalid_alert = VALID_ALERT.copy()
    invalid_alert["severity"] = "invalid"
    response = client.post("/webhook", json=invalid_alert)
    assert response.status_code == 422

def test_missing_alert_name_is_rejected():
    invalid_alert = VALID_ALERT.copy()
    del invalid_alert["alert_name"]
    response = client.post("/webhook", json=invalid_alert)
    assert response.status_code == 422


from app.database import engine, Base
from app.model import AlertDB

def test_alert_is_saved_to_db():
# Create the database tables
    Base.metadata.create_all(bind=engine)

        # Send a valid alert
    response = client.post("/webhook", json=VALID_ALERT)
    assert response.status_code == 200       
    # Check that the alert was saved to the database
    from app.database import SessionLocal
    session = SessionLocal()
    alert_in_db = session.query(AlertDB).order_by(AlertDB.id.desc()).first()
    print(alert_in_db)
    assert alert_in_db is not None
    assert alert_in_db.alert_name == VALID_ALERT["alert_name"]
    assert alert_in_db.service == VALID_ALERT["service"]
    assert alert_in_db.severity == VALID_ALERT["severity"]  
    assert alert_in_db.get_labels() == VALID_ALERT["labels"]
    session.close()

def test_labels_rounded_trip():
    Base.metadata.create_all(bind=engine)
    response = client.post("/webhook", json=VALID_ALERT)
    assert response.status_code == 200
    from app.database import SessionLocal
    session = SessionLocal()
    saved = session.query(AlertDB).filter_by(
        alert_name="High CPU Usage"
    ).first()
    assert saved is not None
    assert saved.get_labels() == VALID_ALERT["labels"]
    session.close()

    labels = saved.get_labels()
    assert labels['env'] == VALID_ALERT["labels"]["env"]

from unittest.mock import patch, MagicMock

def test_analysis_saved_to_db():
    mock_response = MagicMock()                # 5
    mock_response.output_text = (
        "Root cause: CPU spike from unthrottled batch job. "
        "Steps: 1) Scale pods 2) Add rate limiter 3) Alert tuning."
    )

    with patch(                                # 6
        "app.analyzer.OpenAI"
    ) as mock_openai:
        mock_openai.return_value\
            .responses.create\
            .return_value = mock_response      # 7

        response = client.post("/webhook", json=VALID_ALERT)

    assert response.status_code == 200

    from app.database import SessionLocal
    db = SessionLocal()
    saved = db.query(AlertDB).filter_by(
        alert_name="High CPU Usage"
    ).order_by(AlertDB.id.desc()).first()
    db.close()

    assert saved.analysis is not None          # 8
    assert "Root cause" in saved.analysis


def test_analysis_failure_still_saves_alert(): # 9
    with patch("app.analyzer.OpenAI") as mock_openai:
        mock_openai.return_value\
            .responses.create\
            .side_effect = Exception("API down")
        response = client.post("/webhook", json=VALID_ALERT)
    assert response.status_code == 200 

from unittest.mock import patch, MagicMock
def test_rag_context_injectected_into_prompt():    
    captured_prompt = {}
    def mock_create(*args, **kwargs):
        captured_prompt["input"] = kwargs.get("input", "")
        mock_response = MagicMock()
        mock_response.output_text = "Mocked analysis response"
        return mock_response
    
    with patch("app.analyzer.get_similar_postmortems", return_value = [ "Past incident: batch job caused CPU spike."]):
             
        with patch("app.analyzer.OpenAI") as mock_client:
            mock_client.return_value\
                .responses.create\
                .side_effect = mock_create
            response = client.post("/webhook", json=VALID_ALERT)
    assert response.status_code == 200
    prompt_text = captured_prompt["input"]
    assert "Past incident: batch job caused CPU spike." in prompt_text
    assert "High CPU Usage" in prompt_text


def test_slack_notified_on_valid_alert():          # 3
    with patch("app.analyzer.OpenAI") as mock_llm:
        mock_llm.return_value.responses.create.return_value.output_text = "Test analysis"

        with patch("app.notifier.WebhookClient") as mock_slack:  # 4
            mock_slack.return_value.send\
                .return_value.status_code = 200

            response = client.post("/webhook", json=VALID_ALERT)

    assert response.status_code == 200
    mock_slack.return_value.send.assert_called_once()  # 5


def test_slack_failure_does_not_affect_response(): # 6
    with patch("app.analyzer.OpenAI") as mock_llm:
        mock_llm.return_value.responses.create.return_value.output_text = "Test analysis"

        with patch("app.notifier.WebhookClient") as mock_slack:
            mock_slack.return_value.send\
                .side_effect = Exception("Slack is down")

            response = client.post("/webhook", json=VALID_ALERT)

    assert response.status_code == 200