"""
Security Plugin System

Extensible security detection framework for TensorWall.
Add custom detectors for prompt injection, PII, secrets, and more.

Usage:
    from backend.application.engines.security_plugins import PluginManager, SecurityPlugin

    class MyCustomPlugin(SecurityPlugin):
        name = "my_plugin"

        def check(self, messages: list[dict]) -> list[SecurityFinding]:
            # Your detection logic
            return findings

    plugin_manager.register(MyCustomPlugin())
"""

from backend.application.engines.security_plugins.base import (
    SecurityPlugin,
    SecurityFinding,
    RiskLevel,
)
from backend.application.engines.security_plugins.manager import PluginManager

# Default plugin manager
plugin_manager = PluginManager()

__all__ = [
    "SecurityPlugin",
    "SecurityFinding",
    "RiskLevel",
    "PluginManager",
    "plugin_manager",
]
