"""Configuration management for Legal Research Assistant MCP."""

import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Server configuration
    log_level: str = Field(default="INFO", description="Logging level")
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
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


# Global settings instance
settings = Settings()
settings.configure_logging()

# Create cache directory if it doesn't exist
settings.network_cache_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
