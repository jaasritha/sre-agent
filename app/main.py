
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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


SAMPLE_ALERTS = [
    {
        "alert_name": "HighCPU",
        "service": "payment-service",
        "severity": "critical",
        "labels": {"env": "production"},
    },
    {
        "alert_name": "DBLatency",
        "service": "orders-service",
        "severity": "warning",
        "labels": {"env": "staging"},
    },
    {
        "alert_name": "PodCrashLoop",
        "service": "checkout-service",
        "severity": "critical",
        "labels": {"env": "production", "cluster": "us-east-1"},
    },
]


@app.get("/", response_class=HTMLResponse)
def home():
    cards = []
    for idx, alert in enumerate(SAMPLE_ALERTS):
        labels = ", ".join(f"{key}={value}" for key, value in alert["labels"].items())
        cards.append(
            f'''
            <button class="card" data-index="{idx}">
                <div class="card-top">
                    <span class="sev sev-{alert["severity"]}">{alert["severity"]}</span>
                    <span class="service">{alert["service"]}</span>
                </div>
                <h3>{alert["alert_name"]}</h3>
                <p>{labels}</p>
            </button>
            '''
        )

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>SRE-Agent with AI</title>
        <style>
            :root {{
                color-scheme: dark;
                --bg: #0b1020;
                --panel: #121a2f;
                --panel-2: #17213a;
                --text: #e6ecff;
                --muted: #93a4c3;
                --accent: #4f8cff;
                --accent-2: #7c5cff;
                --border: rgba(255,255,255,0.08);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: radial-gradient(circle at top, #152347 0, var(--bg) 45%);
                color: var(--text);
            }}
            .wrap {{
                max-width: 920px;
                margin: 0 auto;
                padding: 40px 20px 56px;
            }}
            h1 {{
                margin: 0 0 8px;
                font-size: 40px;
                letter-spacing: -0.03em;
            }}
            .sub {{ color: var(--muted); margin: 0 0 28px; }}
            .grid {{ display: grid; gap: 14px; }}
            .card {{
                width: 100%;
                text-align: left;
                border: 1px solid var(--border);
                background: linear-gradient(180deg, var(--panel), var(--panel-2));
                color: inherit;
                border-radius: 18px;
                padding: 18px 20px;
                cursor: pointer;
                transition: transform .15s ease, border-color .15s ease;
            }}
            .card:hover {{ transform: translateY(-2px); border-color: rgba(79,140,255,.45); }}
            .card.selected {{ outline: 2px solid var(--accent); }}
            .card-top {{ display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }}
            .sev {{
                display: inline-flex;
                align-items: center;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .08em;
            }}
            .sev-critical {{ background: rgba(224,30,90,.16); color: #ff6b97; }}
            .sev-warning {{ background: rgba(236,178,46,.16); color: #ffd47a; }}
            .sev-info {{ background: rgba(54,197,240,.16); color: #8be7ff; }}
            .service {{ color: var(--muted); font-size: 14px; }}
            h3 {{ margin: 0 0 6px; font-size: 20px; }}
            p {{ margin: 0; color: var(--muted); }}
            .actions {{ display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap; }}
            .btn {{
                border: 0;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 700;
                cursor: pointer;
            }}
            .btn-primary {{ background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: white; }}
            .status {{ margin-top: 16px; min-height: 24px; color: var(--muted); }}
            code {{ color: #ffb65c; }}
            @media (max-width: 640px) {{ h1 {{ font-size: 32px; }} }}
        </style>
    </head>
    <body>
        <main class="wrap">
            <h1>SRE-Agent with AI</h1>
            <p class="sub">Pick an alert and send it to the webhook.</p>

            <div class="grid" id="alerts">
                {''.join(cards)}
            </div>

            <div class="actions">
                <button class="btn btn-primary" id="postBtn">Post alert</button>
            </div>

            <div class="status" id="status">Selected: <code>HighCPU</code> on <code>payment-service</code></div>
        </main>

        <script>
            const alerts = {SAMPLE_ALERTS!r};
            let selectedIndex = 0;
            const status = document.getElementById('status');
            const cards = Array.from(document.querySelectorAll('.card'));

            function renderSelection() {{
                cards.forEach((card, index) => card.classList.toggle('selected', index === selectedIndex));
                const alert = alerts[selectedIndex];
                status.innerHTML = `Selected: <code>${{alert.alert_name}}</code> on <code>${{alert.service}}</code>`;
            }}

            cards.forEach((card, index) => card.addEventListener('click', () => {{
                selectedIndex = index;
                renderSelection();
            }}));

            document.getElementById('postBtn').addEventListener('click', async () => {{
                const alert = alerts[selectedIndex];
                status.textContent = 'Posting alert...';
                const response = await fetch('/webhook', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(alert),
                }});
                const data = await response.json();
                status.textContent = response.ok
                    ? `Posted: ${{data.message || data.status}}`
                    : `Error: ${{data.detail || 'failed to post alert'}}`;
            }});

            renderSelection();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

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