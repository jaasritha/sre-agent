import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from app.model import AlertEvent
from app.retriever import get_similar_postmortems

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_openai_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
    )
def _build_prompt(alert: AlertEvent) -> str:
    labels_str = "\n".join(f"{key}= {value}" for key, value in alert.labels.items())
    
    # Fetch similar postmortems for context
    similar_postmortems = get_similar_postmortems(
        f"{alert.alert_name} on {alert.service}", k=2
    )
    
    rag_context = ""
    if similar_postmortems:
        rag_context = "\nPast similar incidents:\n"
        for doc in similar_postmortems:
            rag_context += f"- {doc}\n"
    
    return f""" Alert details:
- Alert Name: {alert.alert_name}
- Service: {alert.service}
- Severity: {alert.severity}
- Fired At: {alert.fired_at}
- Labels: { labels_str if labels_str else "None" }
{rag_context}
Provide : 
1. Most probable cause of the alert (2 sentences max)
2. Three immediate actions to investigate or mitigate the issue (bullet points)
3. One preventive measure to avoid similar issues in the future (1 sentence)
"""


def _extract_response_text(response) -> str:
    text = getattr(response, "output_text", "") or ""
    if text:
        return text

    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "message":
            content = getattr(item, "content", []) or []
            for part in content:
                if getattr(part, "type", None) == "output_text" and getattr(part, "text", ""):
                    return part.text

        if getattr(item, "type", None) == "reasoning":
            summaries = getattr(item, "summary", []) or []
            for summary in summaries:
                if getattr(summary, "type", None) == "summary_text" and getattr(summary, "text", ""):
                    return summary.text

    return "Error analyzing alert"

def analyze_alert(alert: AlertEvent) -> str:
    logger.info(f"Analyzing alert: {alert.alert_name} for service {alert.service}")
    client = _get_openai_client()
    prompt = _build_prompt(alert)
    logger.debug(f"Generated prompt for analysis:\n{prompt}")
    try:
        response = client.responses.create(
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            instructions="You are an experienced SRE engineer. Provide concise and actionable analysis.",
            input=prompt,
            max_output_tokens=300,
            temperature=0.3,
            reasoning={"effort": "none"},
        )
        response_text = _extract_response_text(response)
        logger.debug(f"Received response from model:\n{response_text}")
        return response_text
    except Exception as e:
        logger.error(f"Error analyzing alert: {e}")
        return "Error analyzing alert"