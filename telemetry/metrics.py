"""In-memory request metrics tracking for telemetry."""

import time
import threading
from collections import defaultdict
from typing import Dict, List


class MetricsCollector:
    """Thread-safe in-memory metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._latencies: List[float] = []
        self._requests_by_provider: Dict[str, int] = defaultdict(int)
        self._requests_by_file_type: Dict[str, int] = defaultdict(int)
        self._total_tokens = 0

    def record_request(
        self,
        latency_ms: float,
        provider: str,
        file_type: str,
        success: bool,
        tokens: int = 0,
    ) -> None:
        """Record metrics for a completed request."""
        with self._lock:
            self._total_requests += 1
            self._latencies.append(latency_ms)

            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

            self._requests_by_provider[provider] += 1
            self._requests_by_file_type[file_type] += 1
            self._total_tokens += tokens

            # Keep only last 10,000 latency entries to avoid memory growth
            if len(self._latencies) > 10000:
                self._latencies = self._latencies[-5000:]

    def get_metrics(self) -> dict:
        """Return current metrics snapshot."""
        with self._lock:
            latencies = sorted(self._latencies) if self._latencies else [0]
            avg = sum(latencies) / len(latencies) if latencies else 0

            return {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "average_latency_ms": round(avg, 2),
                "p95_latency_ms": round(self._percentile(latencies, 95), 2),
                "p99_latency_ms": round(self._percentile(latencies, 99), 2),
                "requests_by_provider": dict(self._requests_by_provider),
                "requests_by_file_type": dict(self._requests_by_file_type),
                "total_tokens_used": self._total_tokens,
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    @staticmethod
    def _percentile(sorted_data: List[float], p: float) -> float:
        """Calculate the p-th percentile from sorted data."""
        if not sorted_data:
            return 0
        idx = max(0, int(len(sorted_data) * p / 100) - 1)
        return sorted_data[min(idx, len(sorted_data) - 1)]


# Global metrics instance
metrics = MetricsCollector()
