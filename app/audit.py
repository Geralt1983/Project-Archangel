import json
import time
import sys

def log_event(event_type: str, data: dict):
    rec = {"ts": int(time.time()), "event": event_type, **data}
    sys.stdout.write(json.dumps(rec) + "\n")
    sys.stdout.flush()