"""
Security Plugin Manager

Manages registration, execution, and lifecycle of security plugins.
"""

import asyncio
import logging
from typing import Optional
from pydantic import BaseModel

from backend.application.engines.security_plugins.base import (
    SecurityPlugin,
    AsyncSecurityPlugin,
    SecurityFinding,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class PluginCheckResult(BaseModel):
    """Aggregated result from all plugins."""

    safe: bool
    risk_level: str
    risk_score: float
    findings: list[SecurityFinding]
    plugins_executed: list[str]
    plugins_failed: list[str]

    def to_api_response(self) -> dict:
        """Format for API response."""
        return {
            "safe": self.safe,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "issues_count": len(self.findings),
            "plugins_executed": self.plugins_executed,
            "findings": [f.model_dump() for f in self.findings],
        }


class PluginManager:
    """
    Manages security plugins.

    Features:
    - Register/unregister plugins
    - Execute all plugins in parallel
    - Aggregate findings
    - Enable/disable plugins at runtime
    """

    def __init__(self):
        self._plugins: dict[str, SecurityPlugin] = {}
        self._initialized: bool = False

    def register(self, plugin: SecurityPlugin) -> None:
        """
        Register a security plugin.

        Args:
            plugin: Plugin instance to register
        """
        if plugin.name in self._plugins:
            logger.warning(f"Replacing existing plugin: {plugin.name}")

        self._plugins[plugin.name] = plugin
        logger.info(f"Registered security plugin: {plugin.name} v{plugin.version}")

        # Initialize if manager is already initialized
        if self._initialized:
            try:
                plugin.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin.name}: {e}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a plugin by name.

        Args:
            name: Plugin name

        Returns:
            True if plugin was unregistered
        """
        if name in self._plugins:
            plugin = self._plugins.pop(name)
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of {name}: {e}")
            logger.info(f"Unregistered security plugin: {name}")
            return True
        return False

    def get_plugin(self, name: str) -> Optional[SecurityPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """List all registered plugins."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "enabled": p.enabled,
                "async": isinstance(p, AsyncSecurityPlugin),
            }
            for p in self._plugins.values()
        ]

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False

    def initialize_all(self) -> None:
        """Initialize all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                plugin.initialize()
                logger.debug(f"Initialized plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize plugin {name}: {e}")
        self._initialized = True

    def cleanup_all(self) -> None:
        """Cleanup all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of {name}: {e}")
        self._initialized = False

    def check(self, messages: list[dict]) -> PluginCheckResult:
        """
        Run all sync plugins and return aggregated results.

        For async plugins, use check_async().
        """
        findings: list[SecurityFinding] = []
        plugins_executed: list[str] = []
        plugins_failed: list[str] = []

        for name, plugin in self._plugins.items():
            if not plugin.enabled:
                continue

            if isinstance(plugin, AsyncSecurityPlugin):
                # Skip async plugins in sync check
                continue

            try:
                plugin_findings = plugin.check(messages)
                findings.extend(plugin_findings)
                plugins_executed.append(name)
            except Exception as e:
                logger.error(f"Plugin {name} failed: {e}")
                plugins_failed.append(name)

        return self._aggregate_results(findings, plugins_executed, plugins_failed)

    async def check_async(self, messages: list[dict]) -> PluginCheckResult:
        """
        Run all plugins (sync and async) and return aggregated results.
        """
        findings: list[SecurityFinding] = []
        plugins_executed: list[str] = []
        plugins_failed: list[str] = []

        # Prepare tasks
        sync_plugins = []
        async_tasks = []

        for name, plugin in self._plugins.items():
            if not plugin.enabled:
                continue

            if isinstance(plugin, AsyncSecurityPlugin):
                async_tasks.append((name, plugin.check_async(messages)))
            else:
                sync_plugins.append((name, plugin))

        # Run sync plugins
        for name, plugin in sync_plugins:
            try:
                plugin_findings = plugin.check(messages)
                findings.extend(plugin_findings)
                plugins_executed.append(name)
            except Exception as e:
                logger.error(f"Plugin {name} failed: {e}")
                plugins_failed.append(name)

        # Run async plugins concurrently
        if async_tasks:
            results = await asyncio.gather(
                *[task for _, task in async_tasks], return_exceptions=True
            )

            for (name, _), result in zip(async_tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Async plugin {name} failed: {result}")
                    plugins_failed.append(name)
                else:
                    findings.extend(result)
                    plugins_executed.append(name)

        return self._aggregate_results(findings, plugins_executed, plugins_failed)

    def _aggregate_results(
        self,
        findings: list[SecurityFinding],
        plugins_executed: list[str],
        plugins_failed: list[str],
    ) -> PluginCheckResult:
        """Aggregate findings into a single result."""
        if not findings:
            return PluginCheckResult(
                safe=True,
                risk_level="low",
                risk_score=0.0,
                findings=[],
                plugins_executed=plugins_executed,
                plugins_failed=plugins_failed,
            )

        # Calculate max risk level
        risk_order = [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        max_risk = max(findings, key=lambda f: risk_order.index(RiskLevel(f.severity)))

        # Calculate risk score
        weights = {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.3,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 1.0,
        }
        total_weight = sum(
            weights.get(RiskLevel(f.severity), 0.1) * f.confidence for f in findings
        )
        risk_score = min(total_weight / 2.0, 1.0)

        return PluginCheckResult(
            safe=False,
            risk_level=(
                max_risk.severity
                if isinstance(max_risk.severity, str)
                else max_risk.severity.value
            ),
            risk_score=round(risk_score, 2),
            findings=findings,
            plugins_executed=plugins_executed,
            plugins_failed=plugins_failed,
        )
