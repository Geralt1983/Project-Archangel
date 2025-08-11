from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import time
import os
from typing import Dict, Any, Optional

router = APIRouter(prefix="/usage", tags=["usage"])

def get_usage_data_path() -> Path:
    """Get the path to usage data file."""
    # Try common locations for usage monitor data
    possible_paths = [
        Path(".local/usage/latest.json"),
        Path("logs/usage_latest.json"),
        Path("/tmp/claude_usage_latest.json"),
        Path.home() / ".claude-usage" / "latest.json"
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # Default path (may not exist yet)
    return Path(".local/usage/latest.json")

@router.get("/latest")
def latest():
    """Get latest Claude Code usage statistics."""
    try:
        usage_file = get_usage_data_path()
        
        if not usage_file.exists():
            return {
                "ok": False, 
                "message": "No usage data yet. Start monitor with 'make usage'",
                "suggestions": [
                    "Run 'make usage' in a separate terminal",
                    "Ensure claude-code-usage-monitor is installed",
                    "Check CLAUDE_CONFIG_DIR environment variable"
                ]
            }
        
        # Read the latest usage data
        data = json.loads(usage_file.read_text())
        data["ts_read"] = time.time()
        data["file_age_seconds"] = time.time() - usage_file.stat().st_mtime
        
        return {"ok": True, "data": data}
        
    except json.JSONDecodeError as e:
        return {"ok": False, "message": f"Invalid usage data format: {e}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def status():
    """Get usage monitoring status and configuration."""
    usage_file = get_usage_data_path()
    claude_config = os.getenv("CLAUDE_CONFIG_DIR", f"{Path.home()}/Library/Application Support/Claude")
    
    return {
        "monitor_installed": _check_monitor_installed(),
        "usage_file_path": str(usage_file),
        "usage_file_exists": usage_file.exists(),
        "claude_config_dir": claude_config,
        "claude_config_exists": Path(claude_config).exists(),
        "suggestions": [
            "Run 'make usage' to start monitoring",
            "Run 'make dev' for full development environment",
            "Configure usage monitor to write to " + str(usage_file)
        ]
    }

@router.get("/predictions")
def predictions():
    """Get usage predictions and burn rate analysis."""
    try:
        data_result = latest()
        if not data_result["ok"]:
            return data_result
        
        usage_data = data_result["data"]
        
        # Extract prediction data if available
        predictions = {}
        if "burn_rate_per_hour" in usage_data:
            burn_rate = usage_data["burn_rate_per_hour"]
            remaining = usage_data.get("tokens_remaining", 0)
            
            if burn_rate > 0:
                hours_remaining = remaining / burn_rate
                predictions = {
                    "hours_remaining": hours_remaining,
                    "minutes_remaining": hours_remaining * 60,
                    "exhaustion_time": time.time() + (hours_remaining * 3600),
                    "warning_30min": hours_remaining < 0.5,
                    "warning_10min": hours_remaining < (10/60),
                    "burn_rate_per_hour": burn_rate
                }
        
        return {
            "ok": True,
            "predictions": predictions,
            "raw_data": usage_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _check_monitor_installed() -> bool:
    """Check if claude-code-usage-monitor is installed."""
    import subprocess
    try:
        # Try common command names
        for cmd in ["claude-monitor", "claude_monitor"]:
            result = subprocess.run(
                ["which", cmd], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                return True
        return False
    except Exception:
        return False

@router.post("/configure")
def configure_monitor(log_file: str = ".local/usage/latest.json"):
    """Configure usage monitor to write to specified log file."""
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a simple config template
        config = {
            "log_file": str(log_path),
            "update_interval_seconds": 30,
            "prediction_window_hours": 1,
            "warning_thresholds": {
                "30_minutes": True,
                "10_minutes": True
            }
        }
        
        # Write initial empty usage file
        log_path.write_text(json.dumps({
            "configured_at": time.time(),
            "message": "Waiting for usage monitor to start..."
        }))
        
        return {
            "ok": True,
            "log_file": str(log_path),
            "config": config,
            "next_steps": [
                f"Start monitor with: make usage",
                f"Configure monitor to write to {log_path}",
                f"Check status with: curl localhost:8000/usage/status"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))