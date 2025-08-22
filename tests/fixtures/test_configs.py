"""
Test configuration fixtures for MCP integration testing
Provides various configuration scenarios for comprehensive testing
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import tempfile
import os


class MCPConfigFixtures:
    """Configuration fixtures for MCP testing"""
    
    @staticmethod
    def minimal_config() -> Dict[str, Any]:
        """Minimal working configuration"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp"
            },
            "features": {
                "enabled_tools": ["create_task", "get_task"],
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress", 
                    "review": "review",
                    "done": "completed",
                    "closed": "completed"
                }
            }
        }
    
    @staticmethod
    def full_featured_config() -> Dict[str, Any]:
        """Comprehensive configuration with all features"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "transport": "http",
                "health_check_interval": 30,
                "connection_timeout": 10,
                "request_timeout": 30,
                "max_retries": 3
            },
            "authentication": {
                "clickup_api_key": "${CLICKUP_API_KEY}",
                "team_id": "${CLICKUP_TEAM_ID}",
                "workspace_id": "${CLICKUP_WORKSPACE_ID:-}",
                "space_id": "${CLICKUP_SPACE_ID:-}",
                "list_id": "${CLICKUP_LIST_ID:-}"
            },
            "features": {
                "enabled_tools": [
                    "create_task", "get_task", "update_task", "delete_task",
                    "list_tasks", "search_tasks", "get_task_comments",
                    "add_task_comment", "get_task_time_tracked", "track_time",
                    "get_lists", "get_spaces", "get_workspaces", "get_teams",
                    "get_workspace_members", "get_task_members",
                    "resolve_user_by_email", "resolve_user_by_username"
                ],
                "disabled_tools": ["delete_doc", "create_webhook", "delete_webhook"]
            },
            "performance": {
                "max_concurrent_requests": 5,
                "request_batch_size": 10,
                "cache_ttl": 300,
                "tool_timeouts": {
                    "default": 30,
                    "list_tasks": 60,
                    "search_tasks": 60,
                    "get_docs": 45
                }
            },
            "security": {
                "validate_responses": True,
                "sanitize_inputs": True,
                "log_level": "INFO",
                "max_request_size": 1048576,
                "max_response_size": 10485760
            },
            "logging": {
                "enable_request_logging": True,
                "enable_response_logging": False,
                "log_sensitive_data": False,
                "max_log_size": "100MB",
                "backup_count": 5
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "sync_with_outbox": True,
                "use_idempotency_keys": True,
                "preserve_audit_trail": True,
                "priority_mapping": {
                    "1": 4, "2": 3, "3": 3, "4": 2, "5": 1
                },
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress",
                    "review": "review",
                    "done": "completed",
                    "closed": "completed"
                }
            },
            "monitoring": {
                "metrics_enabled": True,
                "tracing_enabled": True,
                "error_rate_threshold": 0.05,
                "response_time_threshold": 5000,
                "availability_threshold": 0.99,
                "metrics": [
                    {
                        "name": "mcp_requests_total",
                        "type": "counter",
                        "labels": ["tool", "status"]
                    },
                    {
                        "name": "mcp_request_duration_seconds",
                        "type": "histogram",
                        "labels": ["tool"]
                    },
                    {
                        "name": "mcp_server_available",
                        "type": "gauge",
                        "labels": ["endpoint"]
                    }
                ]
            },
            "development": {
                "debug_mode": False,
                "mock_responses": False,
                "test_data_path": "tests/fixtures/mcp_responses",
                "local_server_port": 3231,
                "local_server_host": "localhost"
            }
        }
    
    @staticmethod
    def high_performance_config() -> Dict[str, Any]:
        """Configuration optimized for high performance"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 5,
                "request_timeout": 15,
                "max_retries": 2
            },
            "features": {
                "enabled_tools": ["create_task", "get_task", "update_task", "list_tasks"],
                "disabled_tools": ["search_tasks", "get_task_comments"]  # Disable slower operations
            },
            "performance": {
                "max_concurrent_requests": 10,
                "request_batch_size": 20,
                "cache_ttl": 600,  # Longer cache TTL
                "tool_timeouts": {
                    "default": 15,
                    "list_tasks": 30
                }
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "sync_with_outbox": False,  # Disable for performance
                "use_idempotency_keys": False,  # Disable for performance
                "priority_mapping": {"1": 4, "2": 3, "3": 3, "4": 2, "5": 1}
            },
            "logging": {
                "enable_request_logging": False,  # Disable for performance
                "enable_response_logging": False,
                "log_level": "WARN"
            }
        }
    
    @staticmethod
    def security_focused_config() -> Dict[str, Any]:
        """Configuration with enhanced security settings"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 15,
                "request_timeout": 45,
                "max_retries": 1  # Reduced retries for security
            },
            "features": {
                "enabled_tools": ["create_task", "get_task", "update_task"],
                "disabled_tools": [
                    "delete_task", "delete_doc", "create_webhook", 
                    "delete_webhook", "get_workspace_members"  # Restrict sensitive operations
                ]
            },
            "security": {
                "validate_responses": True,
                "sanitize_inputs": True,
                "log_level": "DEBUG",  # Detailed logging for security
                "max_request_size": 524288,   # 512KB - smaller limit
                "max_response_size": 2097152  # 2MB - smaller limit
            },
            "logging": {
                "enable_request_logging": True,
                "enable_response_logging": True,  # Full logging for audit
                "log_sensitive_data": False,
                "preserve_audit_trail": True
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": False,  # No fallback for security
                "use_idempotency_keys": True,
                "preserve_audit_trail": True
            },
            "monitoring": {
                "metrics_enabled": True,
                "tracing_enabled": True,
                "error_rate_threshold": 0.01,  # Stricter threshold
                "response_time_threshold": 3000
            }
        }
    
    @staticmethod
    def development_config() -> Dict[str, Any]:
        """Configuration for development and testing"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 30,
                "request_timeout": 60,
                "max_retries": 5
            },
            "features": {
                "enabled_tools": [
                    "create_task", "get_task", "update_task", "delete_task",
                    "list_tasks", "search_tasks", "get_task_comments"
                ],
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "sync_with_outbox": True,
                "use_idempotency_keys": True,
                "priority_mapping": {"1": 4, "2": 3, "3": 3, "4": 2, "5": 1}
            },
            "logging": {
                "enable_request_logging": True,
                "enable_response_logging": True,
                "log_level": "DEBUG"
            },
            "development": {
                "debug_mode": True,
                "mock_responses": True,
                "test_data_path": "tests/fixtures/mcp_responses"
            }
        }
    
    @staticmethod
    def fallback_only_config() -> Dict[str, Any]:
        """Configuration that only uses adapter fallback"""
        return {
            "server": {
                "host": "unavailable-server",
                "port": 9999,
                "endpoint": "/mcp",
                "max_retries": 1
            },
            "features": {
                "enabled_tools": [],  # No tools enabled
                "disabled_tools": ["create_task", "get_task", "update_task"]
            },
            "integration": {
                "bridge_enabled": False,  # Disabled
                "fallback_to_adapter": True
            }
        }
    
    @staticmethod
    def error_prone_config() -> Dict[str, Any]:
        """Configuration designed to trigger errors for testing"""
        return {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 1,    # Very short timeout
                "request_timeout": 2,       # Very short timeout
                "max_retries": 0            # No retries
            },
            "features": {
                "enabled_tools": ["non_existent_tool"],  # Invalid tool
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": False,  # No fallback
                "priority_mapping": {
                    "invalid": "mapping"  # Invalid mapping
                }
            },
            "security": {
                "max_request_size": 100,    # Very small
                "max_response_size": 100    # Very small
            }
        }


class ConfigFileManager:
    """Utility for creating and managing temporary config files"""
    
    def __init__(self):
        self.temp_files = []
    
    def create_config_file(self, config_data: Dict[str, Any], filename: str = None) -> str:
        """Create a temporary config file and return its path"""
        if filename:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', 
                                                  prefix=f'{filename}_', delete=False)
        else:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', 
                                                  prefix='mcp_config_', delete=False)
        
        yaml.safe_dump(config_data, temp_file, default_flow_style=False)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def cleanup(self):
        """Clean up all temporary config files"""
        for filepath in self.temp_files:
            try:
                os.unlink(filepath)
            except OSError:
                pass  # File already deleted
        self.temp_files.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Convenience functions for common configurations

def get_test_config(config_type: str = "minimal") -> str:
    """Get a temporary config file path for testing
    
    Args:
        config_type: Type of config ('minimal', 'full', 'performance', 
                    'security', 'development', 'fallback', 'error')
    
    Returns:
        Path to temporary config file
    """
    config_map = {
        "minimal": MCPConfigFixtures.minimal_config,
        "full": MCPConfigFixtures.full_featured_config,
        "performance": MCPConfigFixtures.high_performance_config,
        "security": MCPConfigFixtures.security_focused_config,
        "development": MCPConfigFixtures.development_config,
        "fallback": MCPConfigFixtures.fallback_only_config,
        "error": MCPConfigFixtures.error_prone_config
    }
    
    if config_type not in config_map:
        raise ValueError(f"Unknown config type: {config_type}")
    
    config_data = config_map[config_type]()
    manager = ConfigFileManager()
    return manager.create_config_file(config_data, config_type)


def create_custom_config(**overrides) -> str:
    """Create a custom config file with overrides
    
    Args:
        **overrides: Configuration overrides to apply to minimal config
    
    Returns:
        Path to temporary config file
    """
    base_config = MCPConfigFixtures.minimal_config()
    
    # Deep merge overrides
    def deep_merge(base: Dict, override: Dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
    
    deep_merge(base_config, overrides)
    
    manager = ConfigFileManager()
    return manager.create_config_file(base_config, "custom")


# Export commonly used functions
__all__ = [
    'MCPConfigFixtures',
    'ConfigFileManager',
    'get_test_config',
    'create_custom_config'
]