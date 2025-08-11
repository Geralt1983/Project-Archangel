#!/usr/bin/env python3
import json
import sys
from app.scoring import compute_score

def main():
    # Read task from stdin
    task = json.loads(sys.stdin.read())
    
    # Default rules if not provided
    rules = {
        "clients": {
            "default": {
                "importance_bias": 1.0,
                "sla_hours": 72
            }
        }
    }
    
    # Override with client-specific rules if client is specified
    if "client" in task:
        client_name = task["client"]
        if client_name in ["amex", "charis", "chayah"]:
            rules["clients"][client_name] = {
                "importance_bias": 1.2 if client_name == "amex" else 1.0,
                "sla_hours": 48 if client_name == "amex" else 72
            }
    
    # Compute score
    score = compute_score(task, rules)
    
    # Extract computed fields
    result = {
        "score": score,
        "deadline_within_24h": task.get("deadline_within_24h", False),
        "sla_pressure": task.get("sla_pressure", 0.0),
        "task": task,
        "rules": rules
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()