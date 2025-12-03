"""Configuration management for Legal Research Assistant MCP."""

import logging
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.logging_utils import JsonFormatter


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # CourtListener MCP connection
    courtlistener_mcp_url: str = Field(
        default="http://localhost:8000/mcp/",
        description="URL for CourtListener MCP server",
    )

    # CourtListener API configuration
    courtlistener_api_key: str | None = Field(
        default=None,
        description="API key for CourtListener requests",
        validation_alias=AliasChoices("COURT_LISTENER_API_KEY", "COURTLISTENER_API_KEY"),
    )
    courtlistener_base_url: str = Field(
        default="https://www.courtlistener.com/api/rest/v4/",
        description="Base URL for CourtListener API requests",
    )
    courtlistener_timeout: float = Field(
        default=30.0,
        description="Request timeout (seconds) for CourtListener API calls",
    )
    courtlistener_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for CourtListener API requests",
    )
    courtlistener_retry_backoff: float = Field(
        default=1.0,
        description="Initial backoff (seconds) for retrying CourtListener API requests",
    )
    courtlistener_cache_dir: Path = Field(
        default=Path(".cache/courtlistener"),
        description="Directory for caching CourtListener API responses",
    )
    courtlistener_cache_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live (seconds) for cached CourtListener responses",
    )
    courtlistener_search_cache_enabled: bool = Field(
        default=True,
        description="Whether to cache search_opinions responses",
    )
    courtlistener_citing_cache_enabled: bool = Field(
        default=True,
        description="Whether to cache find_citing_cases responses",
    )

    # Server configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string",
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for log messages",
    )
    debug: bool = Field(default=False, description="Debug mode")
    mcp_port: int = Field(default=8001, description="MCP server port")

    # Treatment analysis settings
    treatment_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence threshold for validity assessments",
    )
    max_citing_cases: int = Field(
        default=100,
        description="Maximum number of citing cases to analyze",
    )
    fetch_full_text_strategy: str = Field(
        default="smart",
        description="When to fetch full opinion text: 'always', 'smart', 'negative_only', 'never'",
    )
    max_full_text_fetches: int = Field(
        default=10,
        description="Maximum number of full opinion texts to fetch per analysis",
    )

    # Citation network settings
    network_max_depth: int = Field(
        default=3,
        description="Maximum depth for citation network traversal",
    )
    network_cache_dir: Path = Field(
        default=Path("./citation_networks"),
        description="Directory for caching citation network data",
    )

    def configure_logging(self) -> None:
        """Configure application logging."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))

        # Replace existing handlers with structured JSON output
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())

        root_logger.handlers = [handler]
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format,
            datefmt=self.log_date_format,
        )


# Global settings instance
settings = Settings()
settings.configure_logging()

# Create cache directory if it doesn't exist
settings.network_cache_dir.mkdir(parents=True, exist_ok=True)
settings.courtlistener_cache_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
