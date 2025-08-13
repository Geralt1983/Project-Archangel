"""
Orchestrator Configuration Management
Handles loading, saving, and validating orchestrator configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScoringWeights:
    """Orchestrator scoring weights configuration"""
    importance: float = 0.25
    urgency: float = 0.20
    value: float = 0.15
    time_sensitivity: float = 0.15
    sla_breach: float = 0.20
    fairness: float = 0.05
    
    def validate(self) -> bool:
        """Validate weights sum to 1.0"""
        total = sum([self.importance, self.urgency, self.value, 
                    self.time_sensitivity, self.sla_breach, self.fairness])
        return abs(total - 1.0) < 0.001

@dataclass
class StalenessConfig:
    """Staleness curve configuration"""
    threshold_hours: int = 72
    max_penalty: float = 0.3
    characteristic_time_hours: int = 24
    
@dataclass
class WIPConfig:
    """Work-in-Progress limits configuration"""
    default_limit: int = 3
    limits_by_role: Dict[str, int] = field(
        default_factory=lambda: {
            'junior': 2,
            'senior': 5,
            'lead': 8,
        }
    )
    load_balance_threshold: float = 0.8

@dataclass
class ClientConfig:
    """Client-specific configuration"""
    default_daily_cap_hours: int = 8
    client_caps: Dict[str, int] = field(default_factory=dict)
    fairness_lookback_hours: int = 168  # 1 week

@dataclass
class OrchestratorConfig:
    """Complete orchestrator configuration"""
    version: str = "1.0.0"
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    staleness: StalenessConfig = field(default_factory=StalenessConfig)
    wip: WIPConfig = field(default_factory=WIPConfig)
    client: ClientConfig = field(default_factory=ClientConfig)
    
    # Advanced features
    enable_simulation_mode: bool = False
    enable_ml_predictions: bool = False
    debug_mode: bool = False
    
    def validate(self) -> Dict[str, Any]:
        """Validate entire configuration"""
        errors = []
        warnings = []
        
        # Validate scoring weights
        if not self.scoring_weights.validate():
            errors.append("Scoring weights do not sum to 1.0")
            
        # Validate staleness config
        if self.staleness.threshold_hours < 1:
            errors.append("Staleness threshold must be at least 1 hour")
        if not 0 <= self.staleness.max_penalty <= 1:
            errors.append("Max staleness penalty must be between 0 and 1")
            
        # Validate WIP config
        if self.wip.default_limit < 1:
            errors.append("Default WIP limit must be at least 1")
        if not 0 < self.wip.load_balance_threshold <= 1:
            errors.append("Load balance threshold must be between 0 and 1")
            
        # Validate client config
        if self.client.default_daily_cap_hours < 1:
            errors.append("Default daily cap must be at least 1 hour")
        if self.client.fairness_lookback_hours < 1:
            warnings.append("Very short fairness lookback period")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrchestratorConfig':
        """Create from dictionary"""
        # Handle nested dataclasses
        if 'scoring_weights' in data and isinstance(data['scoring_weights'], dict):
            data['scoring_weights'] = ScoringWeights(**data['scoring_weights'])
        if 'staleness' in data and isinstance(data['staleness'], dict):
            data['staleness'] = StalenessConfig(**data['staleness'])
        if 'wip' in data and isinstance(data['wip'], dict):
            data['wip'] = WIPConfig(**data['wip'])
        if 'client' in data and isinstance(data['client'], dict):
            data['client'] = ClientConfig(**data['client'])
            
        return cls(**data)

class ConfigManager:
    """Manages orchestrator configuration persistence and loading"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "orchestrator_config.json"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def load_config(self) -> OrchestratorConfig:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                config = OrchestratorConfig.from_dict(data)
                logger.info(f"Loaded orchestrator config from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Failed to load config: {e}, using defaults")
                return OrchestratorConfig()
        else:
            logger.info("No config file found, creating default")
            config = OrchestratorConfig()
            self.save_config(config)
            return config
    
    def save_config(self, config: OrchestratorConfig) -> bool:
        """Save configuration to file with backup"""
        try:
            # Validate before saving
            validation = config.validate()
            if not validation['valid']:
                logger.error(f"Cannot save invalid config: {validation['errors']}")
                return False
                
            # Create backup if config exists
            if self.config_file.exists():
                backup_name = f"orchestrator_config_backup_{int(datetime.now().timestamp())}.json"
                backup_path = self.backup_dir / backup_name
                self.config_file.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
                
            # Save new config
            with open(self.config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Saved orchestrator config to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def load_environment_overrides(self, config: OrchestratorConfig) -> OrchestratorConfig:
        """Apply environment variable overrides to config"""
        
        # Scoring weight overrides
        env_mappings = {
            'ORCH_WEIGHT_IMPORTANCE': ('scoring_weights', 'importance'),
            'ORCH_WEIGHT_URGENCY': ('scoring_weights', 'urgency'),
            'ORCH_WEIGHT_VALUE': ('scoring_weights', 'value'),
            'ORCH_WEIGHT_TIME_SENSITIVITY': ('scoring_weights', 'time_sensitivity'),
            'ORCH_WEIGHT_SLA_BREACH': ('scoring_weights', 'sla_breach'),
            'ORCH_WEIGHT_FAIRNESS': ('scoring_weights', 'fairness'),
            
            # Staleness overrides
            'ORCH_STALENESS_THRESHOLD': ('staleness', 'threshold_hours'),
            'ORCH_STALENESS_MAX_PENALTY': ('staleness', 'max_penalty'),
            
            # WIP overrides
            'ORCH_WIP_DEFAULT_LIMIT': ('wip', 'default_limit'),
            'ORCH_WIP_LOAD_BALANCE_THRESHOLD': ('wip', 'load_balance_threshold'),
            
            # Client overrides
            'ORCH_CLIENT_DEFAULT_CAP': ('client', 'default_daily_cap_hours'),
            'ORCH_CLIENT_FAIRNESS_LOOKBACK': ('client', 'fairness_lookback_hours'),
            
            # Feature flags
            'ORCH_SIMULATION_MODE': ('enable_simulation_mode',),
            'ORCH_ML_PREDICTIONS': ('enable_ml_predictions',),
            'ORCH_DEBUG_MODE': ('debug_mode',)
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert string to appropriate type
                    if config_path[-1] in ['importance', 'urgency', 'value', 'time_sensitivity', 
                                          'sla_breach', 'fairness', 'max_penalty', 'load_balance_threshold']:
                        env_value = float(env_value)
                    elif config_path[-1] in ['threshold_hours', 'default_limit', 'default_daily_cap_hours', 
                                            'fairness_lookback_hours']:
                        env_value = int(env_value)
                    elif config_path[-1] in ['enable_simulation_mode', 'enable_ml_predictions', 'debug_mode']:
                        env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    
                    # Apply to config
                    obj = config
                    for attr in config_path[:-1]:
                        obj = getattr(obj, attr)
                    setattr(obj, config_path[-1], env_value)
                    
                    logger.info(f"Applied environment override: {env_var}={env_value}")
                    
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to apply environment override {env_var}: {e}")
        
        return config
    
    def create_preset_configs(self):
        """Create preset configurations for different scenarios"""
        presets = {
            "balanced": OrchestratorConfig(
                scoring_weights=ScoringWeights(
                    importance=0.25, urgency=0.20, value=0.15,
                    time_sensitivity=0.15, sla_breach=0.20, fairness=0.05
                )
            ),
            "urgency_focused": OrchestratorConfig(
                scoring_weights=ScoringWeights(
                    importance=0.15, urgency=0.35, value=0.10,
                    time_sensitivity=0.20, sla_breach=0.15, fairness=0.05
                )
            ),
            "fairness_focused": OrchestratorConfig(
                scoring_weights=ScoringWeights(
                    importance=0.20, urgency=0.15, value=0.15,
                    time_sensitivity=0.10, sla_breach=0.15, fairness=0.25
                )
            ),
            "client_value": OrchestratorConfig(
                scoring_weights=ScoringWeights(
                    importance=0.30, urgency=0.15, value=0.25,
                    time_sensitivity=0.10, sla_breach=0.15, fairness=0.05
                )
            )
        }
        
        preset_dir = self.config_dir / "presets"
        preset_dir.mkdir(exist_ok=True)
        
        for name, config in presets.items():
            preset_file = preset_dir / f"{name}.json"
            with open(preset_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Created preset config: {preset_file}")

# Global configuration manager instance
_config_manager = None
_current_config = None

def get_config_manager() -> ConfigManager:
    """Get global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_orchestrator_config() -> OrchestratorConfig:
    """Get current orchestrator configuration"""
    global _current_config
    if _current_config is None:
        manager = get_config_manager()
        _current_config = manager.load_config()
        _current_config = manager.load_environment_overrides(_current_config)
    return _current_config

def reload_config():
    """Force reload configuration from file"""
    global _current_config
    _current_config = None
    return get_orchestrator_config()

def save_orchestrator_config(config: OrchestratorConfig) -> bool:
    """Save orchestrator configuration"""
    global _current_config
    manager = get_config_manager()
    success = manager.save_config(config)
    if success:
        _current_config = config
    return success

# Initialize on import
from datetime import datetime
if __name__ == "__main__":
    # CLI for config management
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "create-presets":
            manager = get_config_manager()
            manager.create_preset_configs()
            print("Created preset configurations")
        elif sys.argv[1] == "validate":
            config = get_orchestrator_config()
            validation = config.validate()
            print(f"Configuration valid: {validation['valid']}")
            if validation['errors']:
                print(f"Errors: {validation['errors']}")
            if validation['warnings']:
                print(f"Warnings: {validation['warnings']}")
        elif sys.argv[1] == "show":
            config = get_orchestrator_config()
            print(json.dumps(config.to_dict(), indent=2))