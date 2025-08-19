"""
Configuration Validation for Project Archangel
Provides comprehensive validation of application configuration
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, message: str) -> None:
        """Add validation error"""
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"Config validation error: {message}")
    
    def add_warning(self, message: str) -> None:
        """Add validation warning"""
        self.warnings.append(message)
        logger.warning(f"Config validation warning: {message}")


class ConfigValidator:
    """Validates Project Archangel configuration"""
    
    REQUIRED_ENV_VARS = [
        "DATABASE_URL"
    ]
    
    OPTIONAL_ENV_VARS = {
        "API_HOST": "localhost",
        "API_PORT": "8080",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "CACHE_TTL": "300",
        "MAX_CONCURRENT_TASKS": "10",
        "RETRY_MAX_ATTEMPTS": "3",
        "RETRY_BASE_DELAY": "1.0"
    }
    
    def __init__(self) -> None:
        self.result = ValidationResult(is_valid=True, errors=[], warnings=[])
    
    def validate_database_url(self, url: str) -> None:
        """Validate DATABASE_URL format"""
        if not url:
            self.result.add_error("DATABASE_URL cannot be empty")
            return
            
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["sqlite", "postgresql", "postgres"]:
                self.result.add_error(
                    f"Unsupported database scheme: {parsed.scheme}. "
                    "Supported schemes: sqlite, postgresql, postgres"
                )
            
            if parsed.scheme in ["postgresql", "postgres"]:
                if not parsed.hostname:
                    self.result.add_error("PostgreSQL URL must include hostname")
                if not parsed.port:
                    self.result.add_warning("PostgreSQL URL missing port, using default 5432")
                if not parsed.path or parsed.path == "/":
                    self.result.add_error("PostgreSQL URL must include database name")
                    
        except Exception as e:
            self.result.add_error(f"Invalid DATABASE_URL format: {e}")
    
    def validate_numeric_config(self, key: str, value: str, min_val: Optional[float] = None, max_val: Optional[float] = None) -> None:
        """Validate numeric configuration values"""
        try:
            num_val = float(value)
            
            if min_val is not None and num_val < min_val:
                self.result.add_error(f"{key} must be >= {min_val}, got {num_val}")
            
            if max_val is not None and num_val > max_val:
                self.result.add_error(f"{key} must be <= {max_val}, got {num_val}")
                
        except ValueError:
            self.result.add_error(f"{key} must be a valid number, got: {value}")
    
    def validate_boolean_config(self, key: str, value: str) -> None:
        """Validate boolean configuration values"""
        if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
            self.result.add_error(
                f"{key} must be a valid boolean (true/false, 1/0, yes/no), got: {value}"
            )
    
    def validate_log_level(self, level: str) -> None:
        """Validate log level configuration"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() not in valid_levels:
            self.result.add_error(
                f"LOG_LEVEL must be one of {valid_levels}, got: {level}"
            )
    
    def validate_provider_config(self) -> None:
        """Validate provider-specific configuration"""
        # Check for provider API tokens
        provider_tokens = {
            "CLICKUP_API_TOKEN": "ClickUp",
            "TRELLO_API_KEY": "Trello", 
            "TRELLO_API_TOKEN": "Trello",
            "TODOIST_API_TOKEN": "Todoist"
        }
        
        found_providers = []
        for token_var, provider_name in provider_tokens.items():
            if os.getenv(token_var):
                found_providers.append(provider_name)
        
        if not found_providers:
            self.result.add_warning(
                "No provider API tokens configured. "
                "Set CLICKUP_API_TOKEN, TRELLO_API_KEY/TOKEN, or TODOIST_API_TOKEN for provider integration."
            )
        else:
            logger.info(f"Found provider configuration for: {', '.join(set(found_providers))}")
    
    def validate_security_config(self) -> None:
        """Validate security-related configuration"""
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            self.result.add_warning("SECRET_KEY not set. Using default for development only.")
        elif len(secret_key) < 32:
            self.result.add_warning("SECRET_KEY should be at least 32 characters long for security")
        
        # Check for development-only settings in production
        if os.getenv("DEBUG", "").lower() == "true":
            self.result.add_warning("DEBUG mode is enabled. Disable for production deployment.")
    
    def validate_all(self) -> ValidationResult:
        """
        Perform comprehensive configuration validation
        
        Returns:
            ValidationResult with validation status and messages
        """
        logger.info("Starting configuration validation")
        
        # Check required environment variables
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value:
                self.result.add_error(f"Required environment variable {var} is not set")
        
        # Validate DATABASE_URL if present
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            self.validate_database_url(database_url)
        
        # Validate optional configuration with type checking
        config_validations = {
            "API_PORT": lambda v: self.validate_numeric_config("API_PORT", v, 1, 65535),
            "DEBUG": lambda v: self.validate_boolean_config("DEBUG", v),
            "LOG_LEVEL": lambda v: self.validate_log_level(v),
            "CACHE_TTL": lambda v: self.validate_numeric_config("CACHE_TTL", v, 0),
            "MAX_CONCURRENT_TASKS": lambda v: self.validate_numeric_config("MAX_CONCURRENT_TASKS", v, 1, 100),
            "RETRY_MAX_ATTEMPTS": lambda v: self.validate_numeric_config("RETRY_MAX_ATTEMPTS", v, 1, 10),
            "RETRY_BASE_DELAY": lambda v: self.validate_numeric_config("RETRY_BASE_DELAY", v, 0.1, 60.0)
        }
        
        for var, validator in config_validations.items():
            value = os.getenv(var)
            if value:
                try:
                    validator(value)
                except Exception as e:
                    self.result.add_error(f"Error validating {var}: {e}")
        
        # Validate provider configuration
        self.validate_provider_config()
        
        # Validate security configuration  
        self.validate_security_config()
        
        # Log validation summary
        if self.result.is_valid:
            if self.result.warnings:
                logger.info(f"Configuration validation passed with {len(self.result.warnings)} warnings")
            else:
                logger.info("Configuration validation passed successfully")
        else:
            logger.error(f"Configuration validation failed with {len(self.result.errors)} errors")
        
        return self.result
    
    def get_effective_config(self) -> Dict[str, str]:
        """
        Get effective configuration with defaults applied
        
        Returns:
            Dictionary of configuration key-value pairs
        """
        config = {}
        
        # Add required variables
        for var in self.REQUIRED_ENV_VARS:
            config[var] = os.getenv(var, "")
        
        # Add optional variables with defaults
        for var, default in self.OPTIONAL_ENV_VARS.items():
            config[var] = os.getenv(var, default)
        
        return config


def validate_config() -> ValidationResult:
    """
    Convenience function to validate configuration
    
    Returns:
        ValidationResult with validation status and messages
    """
    validator = ConfigValidator()
    return validator.validate_all()


def print_config_summary() -> None:
    """Print configuration validation summary"""
    validator = ConfigValidator()
    result = validator.validate_all()
    
    print("Configuration Validation Summary")
    print("=" * 40)
    print(f"Status: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.is_valid:
        print("\nEffective Configuration:")
        config = validator.get_effective_config()
        for key, value in config.items():
            # Mask sensitive values
            display_value = "***" if "token" in key.lower() or "key" in key.lower() or "secret" in key.lower() else value
            print(f"  {key}: {display_value}")


if __name__ == "__main__":
    print_config_summary()