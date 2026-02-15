"""
Test configuration module for dynamic test environment setup.
Supports local and remote (production) testing with easy configuration.
"""

import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    """Test environment types."""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseType(Enum):
    """Database types for testing."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class TestConfig:
    """Main test configuration class."""
    
    environment: Environment
    database_type: DatabaseType
    database_url: str
    api_base_url: str
    use_cloudinary: bool = True
    cloudinary_url: Optional[str] = None
    run_slow_tests: bool = False
    run_ocr_tests: bool = False
    log_level: str = "INFO"
    # Email testing
    email_test_mode: bool = True
    test_email_recipient: Optional[str] = None
    resend_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "TestConfig":
        """Create config from environment variables."""
        env_name = os.getenv("TEST_ENV", "local").lower()
        
        try:
            environment = Environment[env_name.upper()]
        except KeyError:
            environment = Environment.LOCAL
        
        db_type_name = os.getenv("TEST_DB_TYPE", "sqlite").lower()
        try:
            database_type = DatabaseType[db_type_name.upper()]
        except KeyError:
            database_type = DatabaseType.SQLITE
        
        # Build database URL based on environment and type
        if database_type == DatabaseType.SQLITE:
            database_url = "sqlite:///./test.db"
        else:  # PostgreSQL
            if environment == Environment.LOCAL:
                database_url = os.getenv(
                    "TEST_DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/kabala_test"
                )
            else:
                database_url = os.getenv("TEST_DATABASE_URL", "")
        
        # API base URL
        if environment == Environment.LOCAL:
            api_base_url = os.getenv("TEST_API_URL", "http://localhost:8000")
        else:
            api_base_url = os.getenv("TEST_API_URL", "")
        
        return cls(
            environment=environment,
            database_type=database_type,
            database_url=database_url,
            api_base_url=api_base_url,
            use_cloudinary=os.getenv("TEST_USE_CLOUDINARY", "false").lower() == "true",
            cloudinary_url=os.getenv("CLOUDINARY_URL"),
            run_slow_tests=os.getenv("TEST_RUN_SLOW", "false").lower() == "true",
            run_ocr_tests=os.getenv("TEST_RUN_OCR", "false").lower() == "true",
            log_level=os.getenv("TEST_LOG_LEVEL", "INFO"),
            email_test_mode=os.getenv("EMAIL_TEST_MODE", "true").lower() == "true",
            test_email_recipient=os.getenv("TEST_EMAIL_RECIPIENT", None),
            resend_api_key=os.getenv("RESEND_API_KEY", None),
        )
    
    def is_local(self) -> bool:
        """Check if running locally."""
        return self.environment == Environment.LOCAL
    
    def is_production(self) -> bool:
        """Check if running against production."""
        return self.environment == Environment.PRODUCTION
    
    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"TestConfig(env={self.environment.value}, "
            f"db={self.database_type.value}, "
            f"api_url={self.api_base_url}, "
            f"email_test_mode={self.email_test_mode})"
        )


# Singleton instance
_config_instance: Optional[TestConfig] = None


def get_config() -> TestConfig:
    """Get or create the global test config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = TestConfig.from_env()
    return _config_instance


# Global config instance
CONFIG: Optional[TestConfig] = None


def get_config() -> TestConfig:
    """Get or create global test config."""
    global CONFIG
    if CONFIG is None:
        CONFIG = TestConfig.from_env()
    return CONFIG


def reset_config() -> None:
    """Reset global config (mainly for testing the config itself)."""
    global CONFIG
    CONFIG = None
