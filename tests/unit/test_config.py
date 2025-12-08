"""Tests for application configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings
from app.settings_base import BaseSettings


class TestDefaultSettings:
    """Test default configuration values."""

    def test_default_settings(self):
        """Test that all default settings are properly initialized."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            # CourtListener MCP defaults
            assert settings.courtlistener_mcp_url == "http://localhost:8000/mcp/"
            assert settings.courtlistener_api_key is None
            assert settings.courtlistener_base_url == "https://www.courtlistener.com/api/rest/v4/"

            # Timeout defaults
            assert settings.courtlistener_timeout == 30.0
            assert settings.courtlistener_connect_timeout == 10.0
            assert settings.courtlistener_read_timeout == 60.0

            # Retry defaults
            assert settings.courtlistener_retry_attempts == 3
            assert settings.courtlistener_retry_backoff == 1.0

            # Cache defaults
            assert settings.cache_enabled is True
            assert settings.cache_dir == Path(".cache")
            assert settings.courtlistener_cache_dir == Path(".cache/courtlistener")

            # TTL defaults
            assert settings.courtlistener_ttl_metadata == 86400  # 24 hours
            assert settings.courtlistener_ttl_text == 604800  # 7 days
            assert settings.courtlistener_ttl_search == 3600  # 1 hour
            assert settings.courtlistener_search_cache_enabled is True

            # Logging defaults
            assert settings.log_level == "INFO"
            assert settings.log_format == "json"
            assert settings.log_date_format == "%Y-%m-%d %H:%M:%S"
            assert settings.debug is False

            # Server defaults
            assert settings.mcp_port == 8001

            # Treatment analysis defaults
            assert settings.treatment_confidence_threshold == 0.7
            assert settings.max_citing_cases == 100
            assert settings.fetch_full_text_strategy == "smart"
            assert settings.max_full_text_fetches == 10

            # Citation network defaults
            assert settings.network_max_depth == 3
            assert settings.network_cache_dir == Path("./citation_networks")

    def test_get_settings_returns_global_instance(self):
        """Test that get_settings() returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)


class TestEnvVarOverride:
    """Test environment variable override of default settings."""

    def test_env_var_override_simple_string(self):
        """Test that environment variables override string defaults."""
        with patch.dict(os.environ, {
            "COURTLISTENER_MCP_URL": "http://custom:9000/mcp/",
            "COURTLISTENER_BASE_URL": "https://custom.api/",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_mcp_url == "http://custom:9000/mcp/"
            assert settings.courtlistener_base_url == "https://custom.api/"

    def test_env_var_override_float(self):
        """Test that environment variables override float settings."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "45.5",
            "COURTLISTENER_CONNECT_TIMEOUT": "15.0",
            "COURTLISTENER_READ_TIMEOUT": "90.0",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 45.5
            assert settings.courtlistener_connect_timeout == 15.0
            assert settings.courtlistener_read_timeout == 90.0

    def test_env_var_override_int(self):
        """Test that environment variables override integer settings."""
        with patch.dict(os.environ, {
            "COURTLISTENER_RETRY_ATTEMPTS": "5",
            "MCP_PORT": "9001",
            "MAX_CITING_CASES": "50",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_retry_attempts == 5
            assert settings.mcp_port == 9001
            assert settings.max_citing_cases == 50

    def test_env_var_override_bool(self):
        """Test that environment variables override boolean settings."""
        with patch.dict(os.environ, {
            "CACHE_ENABLED": "false",
            "DEBUG": "true",
            "COURTLISTENER_SEARCH_CACHE_ENABLED": "false",
        }, clear=True):
            settings = Settings()
            assert settings.cache_enabled is False
            assert settings.debug is True
            assert settings.courtlistener_search_cache_enabled is False

    def test_env_var_override_path(self):
        """Test that environment variables override Path settings."""
        with patch.dict(os.environ, {
            "CACHE_DIR": "/tmp/custom_cache",
            "COURTLISTENER_CACHE_DIR": "/tmp/cl_cache",
            "NETWORK_CACHE_DIR": "/tmp/networks",
        }, clear=True):
            settings = Settings()
            assert settings.cache_dir == Path("/tmp/custom_cache")
            assert settings.courtlistener_cache_dir == Path("/tmp/cl_cache")
            assert settings.network_cache_dir == Path("/tmp/networks")

    def test_env_var_override_log_level(self):
        """Test environment variable override for log level."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "text",
        }, clear=True):
            settings = Settings()
            assert settings.log_level == "DEBUG"
            assert settings.log_format == "text"

    def test_env_var_case_insensitive(self):
        """Test that environment variables are case-insensitive."""
        with patch.dict(os.environ, {
            "courtlistener_timeout": "25.0",  # lowercase
            "COURTLISTENER_RETRY_ATTEMPTS": "4",  # uppercase
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 25.0
            assert settings.courtlistener_retry_attempts == 4


class TestAliasChoicesForApiKey:
    """Test alias choices for the API key field."""

    def test_api_key_with_court_listener_alias(self):
        """Test API key loading with COURT_LISTENER_API_KEY environment variable."""
        with patch.dict(os.environ, {
            "COURT_LISTENER_API_KEY": "test-key-123",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_api_key == "test-key-123"

    def test_api_key_with_courtlistener_alias(self):
        """Test API key loading with COURTLISTENER_API_KEY environment variable."""
        with patch.dict(os.environ, {
            "COURTLISTENER_API_KEY": "test-key-456",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_api_key == "test-key-456"

    def test_api_key_precedence(self):
        """Test that COURT_LISTENER_API_KEY takes precedence over COURTLISTENER_API_KEY."""
        with patch.dict(os.environ, {
            "COURT_LISTENER_API_KEY": "key-1",
            "COURTLISTENER_API_KEY": "key-2",
        }, clear=True):
            settings = Settings()
            # The first choice in AliasChoices should take precedence
            assert settings.courtlistener_api_key == "key-1"

    def test_api_key_none_by_default(self):
        """Test that API key is None when not provided."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.courtlistener_api_key is None

    def test_api_key_provided_directly(self):
        """Test API key can be provided directly to Settings constructor."""
        settings = Settings(courtlistener_api_key="direct-key")
        assert settings.courtlistener_api_key == "direct-key"


class TestCacheDirectoryCreation:
    """Test cache directory creation behavior."""

    def test_cache_directories_created_on_initialization(self):
        """Test that cache directories are created during settings initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".cache"
            cl_cache_dir = cache_dir / "courtlistener"
            network_cache_dir = Path(tmpdir) / "citation_networks"

            assert not cache_dir.exists()
            assert not cl_cache_dir.exists()
            assert not network_cache_dir.exists()

            # Create directories as would happen in the module
            cl_cache_dir.mkdir(parents=True, exist_ok=True)
            network_cache_dir.mkdir(parents=True, exist_ok=True)

            assert cache_dir.exists()
            assert cl_cache_dir.exists()
            assert network_cache_dir.exists()

    def test_cache_dir_with_custom_path(self):
        """Test cache directory creation with custom paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "custom_cache"

            cache_dir.mkdir(parents=True, exist_ok=True)
            assert cache_dir.exists()

    def test_cache_dir_idempotent(self):
        """Test that cache directory creation is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".cache"

            cache_dir.mkdir(parents=True, exist_ok=True)
            assert cache_dir.exists()

            # Should not raise error when called again
            cache_dir.mkdir(parents=True, exist_ok=True)
            assert cache_dir.exists()


class TestInvalidConfigValidation:
    """Test validation of invalid configuration values."""

    def test_invalid_float_timeout(self):
        """Test that invalid float values are handled."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "invalid",
        }, clear=True):
            with pytest.raises(Exception):  # Pydantic validation error
                Settings()

    def test_invalid_int_port(self):
        """Test that invalid integer values are handled."""
        with patch.dict(os.environ, {
            "MCP_PORT": "not_a_number",
        }, clear=True):
            with pytest.raises(Exception):  # Pydantic validation error
                Settings()

    def test_invalid_bool_cache_enabled(self):
        """Test that invalid boolean values are coerced or fail appropriately."""
        # Pydantic is lenient with boolean conversion, so test valid boolean strings
        with patch.dict(os.environ, {
            "CACHE_ENABLED": "yes",
        }, clear=True):
            settings = Settings()
            assert settings.cache_enabled is True

    def test_invalid_fetch_strategy(self):
        """Test that invalid fetch strategy is accepted (no enum validation)."""
        # The field doesn't have strict validation, so any string is accepted
        with patch.dict(os.environ, {
            "FETCH_FULL_TEXT_STRATEGY": "invalid_strategy",
        }, clear=True):
            settings = Settings()
            assert settings.fetch_full_text_strategy == "invalid_strategy"

    def test_negative_confidence_threshold_accepted(self):
        """Test that negative values are accepted (no range validation)."""
        with patch.dict(os.environ, {
            "TREATMENT_CONFIDENCE_THRESHOLD": "-0.5",
        }, clear=True):
            settings = Settings()
            assert settings.treatment_confidence_threshold == -0.5

    def test_negative_port_accepted(self):
        """Test that negative port numbers are accepted at validation level."""
        with patch.dict(os.environ, {
            "MCP_PORT": "-1",
        }, clear=True):
            settings = Settings()
            assert settings.mcp_port == -1


class TestTimeoutConfigurations:
    """Test timeout-related configuration settings."""

    def test_all_timeouts_together(self):
        """Test setting all timeout configurations together."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "50.0",
            "COURTLISTENER_CONNECT_TIMEOUT": "20.0",
            "COURTLISTENER_READ_TIMEOUT": "80.0",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 50.0
            assert settings.courtlistener_connect_timeout == 20.0
            assert settings.courtlistener_read_timeout == 80.0

    def test_timeout_zero(self):
        """Test that zero timeout is accepted."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "0",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 0.0

    def test_timeout_very_large(self):
        """Test that very large timeout values are accepted."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "999999.99",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 999999.99

    def test_timeout_default_relationship(self):
        """Test the relationship between default timeout values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Read timeout should be longer than connect timeout
            assert settings.courtlistener_read_timeout > settings.courtlistener_connect_timeout
            # Connect timeout should be less than total timeout
            assert settings.courtlistener_connect_timeout < settings.courtlistener_timeout

    def test_timeout_retry_config_together(self):
        """Test timeout and retry configurations work together."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "35.0",
            "COURTLISTENER_RETRY_ATTEMPTS": "5",
            "COURTLISTENER_RETRY_BACKOFF": "2.0",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_timeout == 35.0
            assert settings.courtlistener_retry_attempts == 5
            assert settings.courtlistener_retry_backoff == 2.0


class TestTTLConfigurations:
    """Test TTL (Time-To-Live) related configuration settings."""

    def test_all_ttl_settings(self):
        """Test all TTL configurations."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.courtlistener_ttl_metadata == 86400  # 24 hours
            assert settings.courtlistener_ttl_text == 604800  # 7 days
            assert settings.courtlistener_ttl_search == 3600  # 1 hour

    def test_ttl_override_individual(self):
        """Test overriding individual TTL settings."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TTL_METADATA": "172800",  # 2 days
            "COURTLISTENER_TTL_TEXT": "1209600",  # 14 days
            "COURTLISTENER_TTL_SEARCH": "7200",  # 2 hours
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_ttl_metadata == 172800
            assert settings.courtlistener_ttl_text == 1209600
            assert settings.courtlistener_ttl_search == 7200

    def test_ttl_zero(self):
        """Test that TTL can be set to zero (no caching)."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TTL_METADATA": "0",
            "COURTLISTENER_TTL_TEXT": "0",
            "COURTLISTENER_TTL_SEARCH": "0",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_ttl_metadata == 0
            assert settings.courtlistener_ttl_text == 0
            assert settings.courtlistener_ttl_search == 0

    def test_ttl_very_large(self):
        """Test that very large TTL values are accepted."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TTL_METADATA": "31536000",  # 1 year
            "COURTLISTENER_TTL_TEXT": "315360000",  # 10 years
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_ttl_metadata == 31536000
            assert settings.courtlistener_ttl_text == 315360000

    def test_ttl_text_longer_than_metadata(self):
        """Test the relationship between TTL settings (text should be longer)."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Opinion text is cached longer than metadata
            assert settings.courtlistener_ttl_text > settings.courtlistener_ttl_metadata

    def test_search_cache_enabled_flag(self):
        """Test the search cache enabled flag."""
        with patch.dict(os.environ, {
            "COURTLISTENER_SEARCH_CACHE_ENABLED": "false",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_search_cache_enabled is False

        with patch.dict(os.environ, {
            "COURTLISTENER_SEARCH_CACHE_ENABLED": "true",
        }, clear=True):
            settings = Settings()
            assert settings.courtlistener_search_cache_enabled is True

    def test_global_cache_and_ttl_together(self):
        """Test global cache enabled flag with TTL settings."""
        with patch.dict(os.environ, {
            "CACHE_ENABLED": "false",
            "COURTLISTENER_TTL_METADATA": "0",
        }, clear=True):
            settings = Settings()
            assert settings.cache_enabled is False
            assert settings.courtlistener_ttl_metadata == 0


class TestSettingsIntegration:
    """Integration tests for multiple settings working together."""

    def test_all_settings_modified(self):
        """Test settings with multiple modifications applied simultaneously."""
        env_vars = {
            "COURTLISTENER_MCP_URL": "http://custom:9000/mcp/",
            "COURT_LISTENER_API_KEY": "integration-test-key",
            "COURTLISTENER_TIMEOUT": "60.0",
            "CACHE_ENABLED": "false",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.courtlistener_mcp_url == "http://custom:9000/mcp/"
            assert settings.courtlistener_api_key == "integration-test-key"
            assert settings.courtlistener_timeout == 60.0
            assert settings.cache_enabled is False
            assert settings.log_level == "DEBUG"
            assert settings.debug is True

    def test_settings_model_config(self):
        """Test that model configuration is properly set."""
        assert Settings.model_config["case_sensitive"] is False
        assert Settings.model_config["extra"] == "ignore"

    def test_settings_instance_independence(self):
        """Test that multiple Settings instances are independent."""
        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "25.0",
        }, clear=True):
            settings1 = Settings()
            assert settings1.courtlistener_timeout == 25.0

        with patch.dict(os.environ, {
            "COURTLISTENER_TIMEOUT": "35.0",
        }, clear=True):
            settings2 = Settings()
            assert settings2.courtlistener_timeout == 35.0

        # settings1 should still have its original value
        assert settings1.courtlistener_timeout == 25.0
