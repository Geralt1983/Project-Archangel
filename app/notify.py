import os, httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL","")

def post_slack(text: str, blocks=None):
    if not SLACK_WEBHOOK_URL:
        return {"ok": False, "error": "no webhook"}
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    r = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=15.0)
    r.raise_for_status()
    return {"ok": True}

def nudge_line(task_id: str, title: str, client: str, provider: str, link: str, days_stale: int, score: float):
    return f"Stale {days_stale}d  client {client}  score {score:.2f}  {title}  {link}"