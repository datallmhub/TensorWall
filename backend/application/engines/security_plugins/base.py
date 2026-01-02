"""
Security Plugin Base Classes

Defines the interface for security plugins.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityFinding(BaseModel):
    """Individual security finding from a plugin."""

    plugin: str  # Plugin name that detected this
    category: str  # Category (prompt_injection, pii, secrets, custom, etc.)
    severity: RiskLevel  # Risk severity
    description: str  # Human-readable description
    pattern_matched: Optional[str] = None  # What triggered the detection
    confidence: float = (
        1.0  # Confidence score (0.0 - 1.0), useful for ML-based detection
    )
    metadata: Optional[dict] = None  # Additional plugin-specific data

    class Config:
        use_enum_values = True


class SecurityPlugin(ABC):
    """
    Base class for security plugins.

    Implement this to create custom security detectors.

    Example:
        class ToxicityPlugin(SecurityPlugin):
            name = "toxicity"
            description = "Detects toxic or harmful content"
            version = "1.0.0"

            def check(self, messages: list[dict]) -> list[SecurityFinding]:
                findings = []
                for msg in messages:
                    if self._is_toxic(msg.get("content", "")):
                        findings.append(SecurityFinding(
                            plugin=self.name,
                            category="toxicity",
                            severity=RiskLevel.HIGH,
                            description="Toxic content detected",
                        ))
                return findings
    """

    # Plugin metadata (override in subclass)
    name: str = "base_plugin"
    description: str = "Base security plugin"
    version: str = "1.0.0"
    enabled: bool = True

    @abstractmethod
    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        """
        Check messages for security issues.

        Args:
            messages: List of chat messages in OpenAI format
                      [{"role": "user", "content": "..."}, ...]

        Returns:
            List of SecurityFinding objects for detected issues
        """
        pass

    def initialize(self) -> None:
        """
        Optional initialization method.
        Override to load models, compile patterns, etc.
        """
        pass

    def cleanup(self) -> None:
        """
        Optional cleanup method.
        Override to release resources.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.enabled})"


class AsyncSecurityPlugin(SecurityPlugin):
    """
    Base class for async security plugins.

    Use for plugins that need to call external APIs or ML models.
    """

    @abstractmethod
    async def check_async(self, messages: list[dict]) -> list[SecurityFinding]:
        """
        Async version of check.
        """
        pass

    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        """Sync wrapper - raises error, use check_async instead."""
        raise NotImplementedError(
            f"{self.name} is an async plugin. Use check_async() instead."
        )
