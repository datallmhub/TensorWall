"""Exporters - .

Provides basic metrics export for observability.
"""

from backend.adapters.prometheus.metrics_adapter import InMemoryMetricsAdapter

# Create a singleton metrics exporter
metrics_exporter = InMemoryMetricsAdapter()

__all__ = ["metrics_exporter"]
