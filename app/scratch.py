
class AlertEvent:

    alert_name: str
    alert_id: str
    severity: str
    description: str


    def __init__(self, alert_id, alert_name, severity, description):
        self.alert_id = alert_id
        self.alert_name = alert_name
        self.severity = severity
        self.description = description

    def __str__(self):
        return f"AlertEvent(id={self.alert_id}, severity={self.severity}, description={self.description})"
    
alert = AlertEvent(alert_id="12345", alert_name="High CPU Usage", severity="Critical", description="CPU usage has exceeded 90% for the last 5 minutes.")    
print(alert)

import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
)

response = client.responses.create(
    model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
    instructions="You are an SRE engineer. Answer directly in plain text.",
    input="What causes HighCPU on a payment service?",
    max_output_tokens=200,
)

print("Model response:", response)
print(response.output_text)