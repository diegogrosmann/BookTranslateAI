"""
Simple tests for the parallel.py module
Testing only classes that actually exist.
"""

import pytest

from src.parallel import RateLimiter, WorkerStats


class TestWorkerStats:
    """Tests for the WorkerStats class."""

    def test_worker_stats_creation(self):
        """Test creation of worker statistics."""
        stats = WorkerStats(worker_id=1)

        assert stats.worker_id == 1
        assert stats.chapters_processed == 0
        assert stats.chunks_processed == 0
        assert stats.errors_count == 0
        assert stats.total_processing_time == 0.0
        assert stats.last_activity is None


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_rate_limiter_creation(self):
        """Test creation of rate limiter."""
        limiter = RateLimiter(calls_per_second=2.0)

        assert limiter.calls_per_second == 2.0
        assert limiter.min_interval == 0.5  # 1/2
        assert limiter.last_call_time == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test basic acquisition of rate limiter."""
        limiter = RateLimiter(calls_per_second=10.0)  # Fast for testing

        # First call should not have significant delay
        await limiter.acquire()

        # Verify that last_call_time was updated
        assert limiter.last_call_time > 0
