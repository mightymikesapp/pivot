"""Tests for async behavior and concurrent operations.

Tests concurrent citation lookups, request throttling, timeout handling,
and circuit breaker patterns.
"""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_concurrent_citation_lookups(mock_client):
    """Test concurrent citation lookups without deadlocks."""
    citations = [
        "410 U.S. 113",   # Roe v. Wade
        "505 U.S. 833",   # Planned Parenthood v. Casey
        "597 U.S. 215",   # Dobbs v. Jackson
    ]

    # Setup mock to return different data for each citation
    def lookup_side_effect(citation):
        return {
            "citation": [citation],
            "caseName": f"Case {citation}",
            "dateFiled": "2020-01-01",
        }

    mock_client.lookup_citation.side_effect = lookup_side_effect

    # Concurrent lookups
    tasks = [mock_client.lookup_citation(citation) for citation in citations]
    results = await asyncio.gather(*tasks)

    # All should succeed
    assert len(results) == 3
    assert all(r is not None for r in results)
    assert results[0]["citation"] == ["410 U.S. 113"]
    assert results[1]["citation"] == ["505 U.S. 833"]
    assert results[2]["citation"] == ["597 U.S. 215"]


@pytest.mark.asyncio
async def test_request_throttling():
    """Test request throttling under high concurrency."""
    request_times = []
    min_interval = 0.1  # Minimum interval between requests

    async def throttled_request(delay=min_interval):
        """Simulated request with throttling."""
        request_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(delay)
        return "success"

    # Create a simple throttler
    semaphore = asyncio.Semaphore(2)  # Allow 2 concurrent requests

    async def throttled_wrapper():
        async with semaphore:
            return await throttled_request()

    # Make 10 concurrent requests with throttling
    start_time = asyncio.get_event_loop().time()
    tasks = [throttled_wrapper() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    end_time = asyncio.get_event_loop().time()

    # All should succeed
    assert len(results) == 10
    assert all(r == "success" for r in results)

    # Total time should reflect throttling (5 batches of 2 at ~0.1s each)
    elapsed = end_time - start_time
    assert elapsed >= 0.4  # At least 5 batches


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test handling of timeouts in async operations."""

    async def slow_operation(delay: float):
        """Operation that may timeout."""
        await asyncio.sleep(delay)
        return "completed"

    async def operation_with_timeout(delay: float, timeout: float):
        """Wrapper that adds timeout."""
        try:
            return await asyncio.wait_for(
                slow_operation(delay),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return "timeout"

    # Fast operation should complete
    result = await operation_with_timeout(0.01, 1.0)
    assert result == "completed"

    # Slow operation should timeout
    result = await operation_with_timeout(1.0, 0.1)
    assert result == "timeout"

    # Multiple concurrent operations with mixed timeouts
    tasks = [
        operation_with_timeout(0.01, 0.5),  # Should complete
        operation_with_timeout(1.0, 0.05),  # Should timeout
        operation_with_timeout(0.02, 0.5),  # Should complete
    ]
    results = await asyncio.gather(*tasks)

    assert results[0] == "completed"
    assert results[1] == "timeout"
    assert results[2] == "completed"


@pytest.mark.asyncio
async def test_circuit_breaker_behavior():
    """Test circuit breaker pattern for handling failures."""

    class CircuitBreaker:
        """Simple circuit breaker implementation for testing."""

        def __init__(self, failure_threshold: int = 3, timeout: float = 1.0):
            self.failure_threshold = failure_threshold
            self.timeout = timeout
            self.failures = 0
            self.last_failure_time = None
            self.state = "closed"  # closed, open, half-open

        async def call(self, func, *args, **kwargs):
            """Execute function through circuit breaker."""
            if self.state == "open":
                # Check if we should transition to half-open
                if (
                    self.last_failure_time is not None
                    and asyncio.get_event_loop().time() - self.last_failure_time >= self.timeout
                ):
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                if self.state == "half-open":
                    self.state = "closed"
                    self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = asyncio.get_event_loop().time()
                if self.failures >= self.failure_threshold:
                    self.state = "open"
                raise e

    # Test circuit breaker
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)

    call_count = 0

    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Operation failed")
        return "success"

    # First two calls should fail
    with pytest.raises(Exception):
        await breaker.call(failing_operation)

    with pytest.raises(Exception):
        await breaker.call(failing_operation)

    # Circuit should now be open
    assert breaker.state == "open"

    # Should raise circuit breaker exception
    with pytest.raises(Exception, match="Circuit breaker is open"):
        await breaker.call(failing_operation)

    # Wait for timeout and try again
    await asyncio.sleep(0.6)

    # Next call should transition through half-open and succeed
    result = await breaker.call(failing_operation)
    assert result == "success"
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_concurrent_citation_network_building(mock_client):
    """Test building citation networks concurrently."""

    async def build_network_for_citation(citation):
        """Simulate building a network for a citation."""
        case = await mock_client.lookup_citation(citation)
        citing_cases = await mock_client.find_citing_cases(citation)
        return {
            "root": case,
            "citing_cases": citing_cases.get("results", []),
        }

    citations = ["410 U.S. 113", "505 U.S. 833"]

    # Mock responses
    mock_client.lookup_citation.return_value = {"caseName": "Test Case", "citation": ["410 U.S. 113"]}
    mock_client.find_citing_cases.return_value = {"results": [{"caseName": "Citing Case"}]}

    # Build networks concurrently
    tasks = [build_network_for_citation(citation) for citation in citations]
    networks = await asyncio.gather(*tasks)

    assert len(networks) == 2
    assert all(n["root"] is not None for n in networks)
    assert all(len(n["citing_cases"]) > 0 for n in networks)


@pytest.mark.asyncio
async def test_fallback_handling_in_async():
    """Test fallback strategies in async operations."""

    async def primary_source(fail=False):
        """Primary data source."""
        if fail:
            raise Exception("Primary source failed")
        await asyncio.sleep(0.01)
        return "primary_data"

    async def fallback_source():
        """Fallback data source."""
        await asyncio.sleep(0.02)
        return "fallback_data"

    async def get_data_with_fallback(use_fallback=False):
        """Get data with fallback strategy."""
        try:
            return await primary_source(fail=use_fallback)
        except Exception:
            return await fallback_source()

    # Should use primary source
    result = await get_data_with_fallback(use_fallback=False)
    assert result == "primary_data"

    # Should fall back to secondary source
    result = await get_data_with_fallback(use_fallback=True)
    assert result == "fallback_data"


@pytest.mark.asyncio
async def test_concurrent_error_handling():
    """Test error handling in concurrent operations."""

    async def operation(operation_id: int, should_fail: bool = False):
        """Operation that may fail."""
        await asyncio.sleep(0.01)
        if should_fail:
            raise Exception(f"Operation {operation_id} failed")
        return f"Operation {operation_id} succeeded"

    # Mix of successful and failing operations
    tasks = [
        operation(1, should_fail=False),
        operation(2, should_fail=True),
        operation(3, should_fail=False),
    ]

    # Use gather with return_exceptions to capture all results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check results
    assert results[0] == "Operation 1 succeeded"
    assert isinstance(results[1], Exception)
    assert str(results[1]) == "Operation 2 failed"
    assert results[2] == "Operation 3 succeeded"


@pytest.mark.asyncio
async def test_rate_limiting_with_retry():
    """Test rate limiting with retry logic."""

    class RateLimiter:
        """Simple rate limiter with retry."""

        def __init__(self, max_retries: int = 3, backoff: float = 0.1):
            self.max_retries = max_retries
            self.backoff = backoff
            self.attempt_times = []

        async def call(self, func, *args, **kwargs):
            """Call function with retry and backoff."""
            for attempt in range(self.max_retries):
                try:
                    self.attempt_times.append(asyncio.get_event_loop().time())
                    return await func(*args, **kwargs)
                except Exception:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(self.backoff * (2 ** attempt))

    limiter = RateLimiter(max_retries=3, backoff=0.05)

    attempt_count = 0

    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = await limiter.call(flaky_operation)
    assert result == "success"
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_task_cancellation():
    """Test proper handling of task cancellation."""

    async def long_running_task(task_id: int):
        """Long-running task that can be cancelled."""
        try:
            for i in range(10):
                await asyncio.sleep(0.1)
                if i == 5:
                    # This is where it might be cancelled
                    pass
            return f"Task {task_id} completed"
        except asyncio.CancelledError:
            return f"Task {task_id} cancelled"

    # Create tasks
    tasks = [asyncio.create_task(long_running_task(i)) for i in range(3)]

    # Let them run for a bit
    await asyncio.sleep(0.3)

    # Cancel one task
    tasks[1].cancel()

    # Gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert "Task 0 completed" in str(results[0]) or "Task 0 cancelled" in str(results[0])
    # Task 1 should be cancelled
    assert isinstance(results[1], asyncio.CancelledError) or str(results[1]).startswith("Task 1 cancelled")


@pytest.mark.asyncio
async def test_context_propagation_in_concurrent_tasks(mock_client):
    """Test that context is properly maintained in concurrent tasks."""

    async def citation_lookup_with_context(citation: str, context_id: str):
        """Lookup with context tracking."""
        result = await mock_client.lookup_citation(citation)
        return {
            "context_id": context_id,
            "citation": citation,
            "result": result,
        }

    # Setup mocks
    mock_client.lookup_citation.return_value = {"caseName": "Test Case"}

    # Run with different context IDs
    tasks = [
        citation_lookup_with_context("410 U.S. 113", "context-1"),
        citation_lookup_with_context("505 U.S. 833", "context-2"),
        citation_lookup_with_context("597 U.S. 215", "context-3"),
    ]

    results = await asyncio.gather(*tasks)

    # Verify context is preserved
    assert results[0]["context_id"] == "context-1"
    assert results[1]["context_id"] == "context-2"
    assert results[2]["context_id"] == "context-3"
