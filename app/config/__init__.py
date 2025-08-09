import os
import yaml
from typing import Dict, Any
from pathlib import Path

_rules_cache = None

def load_rules() -> Dict[str, Any]:
    """Load rules from YAML file with caching."""
    global _rules_cache
    
    if _rules_cache is None:
        config_dir = Path(__file__).parent
        rules_path = config_dir / "rules.yaml"
        
        with open(rules_path, 'r') as f:
            _rules_cache = yaml.safe_load(f)
    
    return _rules_cache

def get_client_config(client_name: str) -> Dict[str, Any]:
    """Get configuration for a specific client."""
    rules = load_rules()
    return rules.get("clients", {}).get(client_name, rules["clients"]["unknown"])

def get_task_type_config(task_type: str) -> Dict[str, Any]:
    """Get configuration for a specific task type."""
    rules = load_rules()
    return rules.get("task_types", {}).get(task_type, rules["task_types"]["general"])

def reload_rules() -> None:
    """Force reload of rules configuration."""
    global _rules_cache
    _rules_cache = None