"""
Testes simples para o módulo parallel.py  
Testando apenas as classes que realmente existem.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from parallel import WorkerStats, RateLimiter


class TestWorkerStats:
    """Testes para a classe WorkerStats."""
    
    def test_worker_stats_creation(self):
        """Testa criação de estatísticas de worker."""
        stats = WorkerStats(worker_id=1)
        
        assert stats.worker_id == 1
        assert stats.chapters_processed == 0
        assert stats.chunks_processed == 0
        assert stats.errors_count == 0
        assert stats.total_processing_time == 0.0
        assert stats.last_activity is None


class TestRateLimiter:
    """Testes para a classe RateLimiter."""
    
    def test_rate_limiter_creation(self):
        """Testa criação do rate limiter."""
        limiter = RateLimiter(calls_per_second=2.0)
        
        assert limiter.calls_per_second == 2.0
        assert limiter.min_interval == 0.5  # 1/2
        assert limiter.last_call_time == 0.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Testa aquisição básica do rate limiter."""
        limiter = RateLimiter(calls_per_second=10.0)  # Rápido para teste
        
        # Primeira chamada não deve ter delay significativo
        await limiter.acquire()
        
        # Verifica que last_call_time foi atualizado
        assert limiter.last_call_time > 0