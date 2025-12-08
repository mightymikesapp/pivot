"""Tests for logging infrastructure including formatters, context managers, and decorators."""

import asyncio
import json
import logging
import time
from io import StringIO
from unittest.mock import MagicMock, patch
from unittest.mock import patch

import pytest

from app.logging_config import (
    JsonFormatter,
    configure_logging,
    correlation_id_ctx,
    request_metadata_ctx,
    tool_logging,
)
from app.logging_utils import log_event, log_operation


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""

    def test_format_basic_log_record(self):
        """Test formatting a basic log record with minimal fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_includes_correlation_id(self):
        """Test that correlation ID is included when set in context."""
        formatter = JsonFormatter()
        correlation_token = correlation_id_ctx.set("test-correlation-123")

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert data["correlation_id"] == "test-correlation-123"
        finally:
            correlation_id_ctx.reset(correlation_token)

    def test_format_includes_tool_name_from_metadata(self):
        """Test that tool_name is included from request metadata."""
        formatter = JsonFormatter()
        metadata_token = request_metadata_ctx.set({"tool_name": "test_tool"})

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert data["tool_name"] == "test_tool"
        finally:
            request_metadata_ctx.reset(metadata_token)

    def test_format_includes_citation_from_metadata(self):
        """Test that citation is included from request metadata."""
        formatter = JsonFormatter()
        metadata_token = request_metadata_ctx.set(
            {"tool_name": "test_tool", "citation": "410 U.S. 113"}
        )

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert data["citation"] == "410 U.S. 113"
        finally:
            request_metadata_ctx.reset(metadata_token)

    def test_format_includes_extra_fields(self):
        """Test that extra fields (elapsed_ms, event, etc.) are included."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.elapsed_ms = 123.45
        record.event = "tool_start"
        record.query_params = {"q": "test"}
        record.citation_count = 5

        result = formatter.format(record)
        data = json.loads(result)

        assert data["elapsed_ms"] == 123.45
        assert data["event"] == "tool_start"
        assert data["query_params"] == {"q": "test"}
        assert data["citation_count"] == 5

    def test_format_includes_exception_info(self):
        """Test that exception information is included when present."""
        formatter = JsonFormatter()
        import sys

        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )
            result = formatter.format(record)
            data = json.loads(result)

            assert "exception" in data
            assert "ValueError: Test error" in data["exception"]

    def test_format_skips_none_extra_fields(self):
        """Test that extra fields with None values are not included."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.elapsed_ms = None
        record.event = None

        result = formatter.format(record)
        data = json.loads(result)

        assert "elapsed_ms" not in data
        assert "event" not in data

    def test_format_output_is_valid_json(self):
        """Test that formatted output is always valid JSON."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Warning with unicode: こんにちは",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "WARNING"
        assert "こんにちは" in data["message"]


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configure_logging_sets_log_level(self):
        """Test that configure_logging sets the root logger level correctly."""
        root_logger = logging.getLogger()
        original_level = root_logger.level

        try:
            configure_logging("DEBUG", "%(message)s")
            assert root_logger.level == logging.DEBUG

            configure_logging("WARNING", "%(message)s")
            assert root_logger.level == logging.WARNING
        finally:
            root_logger.setLevel(original_level)

    def test_configure_logging_with_json_format(self):
        """Test that JSON format is applied when log_format is 'json'."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            configure_logging("INFO", "json")
            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, JsonFormatter)
        finally:
            root_logger.handlers = original_handlers

    def test_configure_logging_with_string_format(self):
        """Test that string format is applied when log_format is not 'json'."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            configure_logging("INFO", "%(levelname)s - %(message)s")
            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, logging.Formatter)
            assert not isinstance(handler.formatter, JsonFormatter)
        finally:
            root_logger.handlers = original_handlers

    def test_configure_logging_with_custom_date_format(self):
        """Test that custom date format is applied."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            configure_logging("INFO", "%(asctime)s - %(message)s", "%Y-%m-%d")
            handler = root_logger.handlers[0]
            assert handler.formatter.datefmt == "%Y-%m-%d"
        finally:
            root_logger.handlers = original_handlers

    def test_configure_logging_replaces_handlers(self):
        """Test that configure_logging replaces existing handlers."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        # Add a dummy handler
        dummy_handler = logging.StreamHandler(StringIO())
        root_logger.addHandler(dummy_handler)

        try:
            configure_logging("INFO", "json")
            assert dummy_handler not in root_logger.handlers
            assert len(root_logger.handlers) == 1
        finally:
            root_logger.handlers = original_handlers


class TestToolLoggingDecorator:
    """Tests for the tool_logging decorator."""

    def test_tool_logging_sync_function_success(self):
        """Test tool_logging decorator on synchronous function with successful execution."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            @tool_logging("test_tool")
            def test_func(arg1: str, arg2: int = 10):
                return f"{arg1}-{arg2}"

            # Call the decorated function
            with patch("app.logging_config.logging.getLogger", return_value=logger):
            with patch("app.logging_config.logging.getLogger", return_value=logger):
                @tool_logging("test_tool")
                def test_func(arg1: str, arg2: int = 10):
                    return f"{arg1}-{arg2}"

                # Call the decorated function
                result = test_func("hello", arg2=20)

            assert result == "hello-20"
            # We should have start and end events
            events = [r.getMessage() for r in log_records if hasattr(r, "event")]
            messages = [record.getMessage() for record in log_records]
            assert "Tool call started" in messages
            assert "Tool call completed" in messages
        finally:
            logger.removeHandler(handler)

    def test_tool_logging_sync_function_exception(self):
        """Test tool_logging decorator on synchronous function with exception."""

        @tool_logging("test_tool")
        def test_func():
            raise ValueError("Test error")

        # Verify that the decorator preserves the exception
        with pytest.raises(ValueError, match="Test error"):
            test_func()

        # Verify correlation ID was cleaned up
        assert correlation_id_ctx.get() is None

    def test_tool_logging_async_function_success(self):
        """Test tool_logging decorator on asynchronous function with successful execution."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            @tool_logging("test_tool")
            async def test_func(arg1: str) -> str:
                await asyncio.sleep(0.01)
                return f"result-{arg1}"

            with patch("app.logging_config.logging.getLogger", return_value=logger):
                result = asyncio.run(test_func("hello"))

            assert result == "result-hello"
        finally:
            logger.removeHandler(handler)

    def test_tool_logging_async_function_exception(self):
        """Test tool_logging decorator on asynchronous function with exception."""

        @tool_logging("test_tool")
        async def test_func():
            await asyncio.sleep(0.01)
            raise ValueError("Async error")

        # Verify that the decorator preserves the exception
        with pytest.raises(ValueError, match="Async error"):
            asyncio.run(test_func())

        # Verify correlation ID was cleaned up
        assert correlation_id_ctx.get() is None

    def test_tool_logging_sets_correlation_id(self):
        """Test that tool_logging decorator sets a correlation ID."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func():
            # Get the correlation ID from context
            return correlation_id_ctx.get()

        correlation_id = test_func()
        assert correlation_id is not None
        assert len(correlation_id) > 0

    def test_tool_logging_sets_metadata(self):
        """Test that tool_logging decorator sets request metadata."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func():
            # Get the metadata from context
            return request_metadata_ctx.get()

        metadata = test_func()
        assert metadata.get("tool_name") == "test_tool"

    def test_tool_logging_preserves_function_metadata(self):
        """Test that tool_logging decorator preserves function name and docstring."""

        @tool_logging("test_tool")
        def test_func():
            """Test function docstring."""
            return "result"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."

    def test_tool_logging_with_citation_argument(self):
        """Test that tool_logging extracts citation from function arguments."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func(citation: str):
            return request_metadata_ctx.get()

        metadata = test_func("410 U.S. 113")
        assert metadata.get("citation") == "410 U.S. 113"

    def test_tool_logging_with_citation_id_argument(self):
        """Test that tool_logging extracts citation_id from function arguments."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func(citation_id: str):
            return request_metadata_ctx.get()

        metadata = test_func("12345")
        assert metadata.get("citation") == "12345"

    def test_tool_logging_with_citation_text_argument(self):
        """Test that tool_logging extracts citation_text from function arguments."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func(citation_text: str):
            return request_metadata_ctx.get()

        metadata = test_func("505 U.S. 833")
        assert metadata.get("citation") == "505 U.S. 833"

    def test_tool_logging_measures_elapsed_time(self):
        """Test that tool_logging decorator measures and logs elapsed time."""

        @tool_logging("test_tool")
        def test_func():
            time.sleep(0.02)  # Sleep for 20ms to ensure measurable elapsed time
            return "result"

        # Capture logs
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            result = test_func()

            assert result == "result"

            # Find records with elapsed_ms - it gets added as an extra field
            elapsed_records = [
                r for r in log_records if hasattr(r, "elapsed_ms") and r.elapsed_ms is not None
            ]
            # At least one record should have elapsed time
            assert len(elapsed_records) >= 1, f"Expected elapsed_ms field in log records, got {[(r.getMessage(), getattr(r, 'elapsed_ms', None)) for r in log_records]}"
            # The elapsed time should be at least 20ms
            assert any(r.elapsed_ms >= 20 for r in elapsed_records), f"Expected elapsed_ms >= 20, got {[r.elapsed_ms for r in elapsed_records]}"
        finally:
            logger.removeHandler(handler)

    def test_tool_logging_cleans_up_context(self):
        """Test that tool_logging decorator cleans up context after execution."""
        logger = logging.getLogger("test")

        @tool_logging("test_tool")
        def test_func():
            pass

        # Before calling
        assert correlation_id_ctx.get() is None

        # Call the function
        test_func()

        # After calling, context should be cleaned up
        assert correlation_id_ctx.get() is None


class TestLogEvent:
    """Tests for the log_event function."""

    def test_log_event_basic(self):
        """Test basic log_event functionality."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Test event")
            assert len(log_records) == 1
            assert log_records[0].getMessage() == "Test event"
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_level(self):
        """Test log_event with custom log level."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.DEBUG)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Debug event", level=logging.DEBUG)
            assert log_records[0].levelno == logging.DEBUG

            log_event(logger, "Warning event", level=logging.WARNING)
            assert log_records[1].levelno == logging.WARNING
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_tool_name(self):
        """Test log_event includes tool_name in extra context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Test", tool_name="my_tool")
            assert log_records[0].tool_name == "my_tool"
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_query_params(self):
        """Test log_event includes query_params."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Test", query_params={"q": "roe", "limit": 10})
            assert log_records[0].query_params == {"q": "roe", "limit": 10}
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_citation_count(self):
        """Test log_event includes citation_count."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Test", citation_count=42)
            assert log_records[0].citation_count == 42
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_event_tag(self):
        """Test log_event includes event tag."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(logger, "Test", event="custom_event")
            assert log_records[0].event == "custom_event"
        finally:
            logger.removeHandler(handler)

    def test_log_event_with_correlation_id(self):
        """Test log_event includes correlation ID from context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        correlation_token = correlation_id_ctx.set("test-correlation-456")

        try:
            log_event(logger, "Test")
            assert log_records[0].correlation_id == "test-correlation-456"
        finally:
            correlation_id_ctx.reset(correlation_token)
            logger.removeHandler(handler)

    def test_log_event_with_extra_context(self):
        """Test log_event includes extra context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            log_event(
                logger,
                "Test",
                extra_context={"custom_field": "custom_value", "request_id": "req-123"},
            )
            assert log_records[0].custom_field == "custom_value"
            assert log_records[0].request_id == "req-123"
        finally:
            logger.removeHandler(handler)


class TestLogOperationContextManager:
    """Tests for the log_operation context manager."""

    def test_log_operation_success(self):
        """Test log_operation logs start and finish on success."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            with log_operation(
                logger, tool_name="test_tool", request_id="req-1", query_params=None, event="test_event"
            ):
                pass

            # Should have two records: start and finish
            assert len(log_records) == 2
            assert "Starting" in log_records[0].getMessage()
            assert "Finished" in log_records[1].getMessage()
        finally:
            logger.removeHandler(handler)

    def test_log_operation_failure(self):
        """Test log_operation logs exception on failure."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            with pytest.raises(ValueError):
                with log_operation(
                    logger, tool_name="test_tool", request_id="req-1", query_params=None, event="test_event"
                ):
                    raise ValueError("Test error")

            # Should have start and exception record
            assert len(log_records) == 2
            assert "Starting" in log_records[0].getMessage()
            assert "failed" in log_records[1].getMessage()
        finally:
            logger.removeHandler(handler)

    def test_log_operation_measures_time(self):
        """Test log_operation measures elapsed time."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            with log_operation(
                logger, tool_name="test_tool", request_id="req-1", query_params=None, event="test_event"
            ):
                time.sleep(0.01)

            # Check finish record has elapsed_ms
            finish_record = log_records[1]
            assert hasattr(finish_record, "elapsed_ms")
            assert finish_record.elapsed_ms >= 10
        finally:
            logger.removeHandler(handler)

    def test_log_operation_with_metadata(self):
        """Test log_operation includes tool_name and other metadata."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            with log_operation(
                logger,
                tool_name="my_tool",
                request_id="req-123",
                query_params={"q": "test"},
                event="operation_event",
            ):
                pass

            start_record = log_records[0]
            assert start_record.tool_name == "my_tool"
            assert start_record.request_id == "req-123"
            assert start_record.query_params == {"q": "test"}
            assert start_record.event == "operation_event"
        finally:
            logger.removeHandler(handler)

    def test_log_operation_with_extra_context(self):
        """Test log_operation includes extra context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            with log_operation(
                logger,
                tool_name="my_tool",
                request_id="req-123",
                query_params=None,
                event="operation_event",
                extra_context={"custom_key": "custom_value"},
            ):
                pass

            start_record = log_records[0]
            assert start_record.custom_key == "custom_value"
        finally:
            logger.removeHandler(handler)

    def test_log_operation_with_correlation_id(self):
        """Test log_operation includes correlation ID from context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        correlation_token = correlation_id_ctx.set("corr-789")

        try:
            with log_operation(
                logger, tool_name="my_tool", request_id=None, query_params=None, event="operation_event"
            ):
                pass

            start_record = log_records[0]
            assert start_record.correlation_id == "corr-789"
        finally:
            correlation_id_ctx.reset(correlation_token)
            logger.removeHandler(handler)

    def test_log_operation_with_metadata_context(self):
        """Test log_operation includes metadata from request context."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        metadata_token = request_metadata_ctx.set(
            {"tool_name": "context_tool", "citation": "410 U.S. 113"}
        )

        try:
            with log_operation(
                logger, tool_name=None, request_id=None, query_params=None, event="operation_event"
            ):
                pass

            start_record = log_records[0]
            assert start_record.tool_name == "context_tool"
            assert start_record.citation == "410 U.S. 113"
        finally:
            request_metadata_ctx.reset(metadata_token)
            logger.removeHandler(handler)


class TestLoggingIntegration:
    """Integration tests combining multiple logging components."""

    def test_decorator_with_log_operation(self):
        """Test tool_logging decorator works with log_operation context manager."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        log_records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = TestHandler()
        logger.addHandler(handler)

        try:
            @tool_logging("test_tool")
            def test_func():
                with log_operation(
                    logger,
                    tool_name="inner_tool",
                    request_id=None,
                    query_params=None,
                    event="inner_event",
                ):
                    return "result"

            with patch("app.logging_config.logging.getLogger", return_value=logger):
                result = test_func()

            assert result == "result"
            # Should have multiple log records from both decorator and context manager
            assert len(log_records) > 0
        finally:
            logger.removeHandler(handler)

    def test_json_formatter_with_all_fields(self):
        """Test JsonFormatter with all possible fields populated."""
        formatter = JsonFormatter()
        correlation_token = correlation_id_ctx.set("all-fields-test")
        metadata_token = request_metadata_ctx.set(
            {"tool_name": "integration_tool", "citation": "505 U.S. 833"}
        )

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Integration test",
                args=(),
                exc_info=None,
            )
            record.elapsed_ms = 42.5
            record.event = "test_event"
            record.query_params = {"search": "roe"}
            record.citation_count = 3

            result = formatter.format(record)
            data = json.loads(result)

            assert data["level"] == "INFO"
            assert data["logger"] == "test.logger"
            assert data["message"] == "Integration test"
            assert data["correlation_id"] == "all-fields-test"
            assert data["tool_name"] == "integration_tool"
            assert data["citation"] == "505 U.S. 833"
            assert data["elapsed_ms"] == 42.5
            assert data["event"] == "test_event"
            assert data["query_params"] == {"search": "roe"}
            assert data["citation_count"] == 3
        finally:
            correlation_id_ctx.reset(correlation_token)
            request_metadata_ctx.reset(metadata_token)
