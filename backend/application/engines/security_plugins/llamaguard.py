"""
LlamaGuard Security Plugin

ML-based content moderation using Meta's Llama Guard model.
Can run locally via Ollama or through an external API.

LlamaGuard Categories:
- S1: Violence and Hate
- S2: Sexual Content
- S3: Criminal Planning
- S4: Guns and Illegal Weapons
- S5: Regulated or Controlled Substances
- S6: Self-Harm
- S7: Code Interpreter Abuse

Requirements:
- Ollama with llama-guard model: ollama pull llama-guard
- Or external LlamaGuard API endpoint
"""

import asyncio
import logging
from typing import Optional
import httpx

from backend.application.engines.security_plugins.base import (
    AsyncSecurityPlugin,
    SecurityFinding,
    RiskLevel,
)

logger = logging.getLogger(__name__)


# LlamaGuard safety categories
LLAMAGUARD_CATEGORIES = {
    "S1": ("Violence and Hate", RiskLevel.CRITICAL),
    "S2": ("Sexual Content", RiskLevel.HIGH),
    "S3": ("Criminal Planning", RiskLevel.CRITICAL),
    "S4": ("Guns and Illegal Weapons", RiskLevel.HIGH),
    "S5": ("Regulated Substances", RiskLevel.MEDIUM),
    "S6": ("Self-Harm", RiskLevel.CRITICAL),
    "S7": ("Code Interpreter Abuse", RiskLevel.HIGH),
    "S8": ("Child Safety", RiskLevel.CRITICAL),
    "S9": ("Defamation", RiskLevel.MEDIUM),
    "S10": ("Specialized Advice", RiskLevel.LOW),
    "S11": ("Elections", RiskLevel.MEDIUM),
}


class LlamaGuardPlugin(AsyncSecurityPlugin):
    """
    LlamaGuard ML-based content moderation plugin.

    Uses Meta's Llama Guard model for nuanced content safety detection.
    Supports both local (Ollama) and remote API endpoints.
    """

    name = "llamaguard"
    description = "ML-based content moderation using Meta's Llama Guard"
    version = "1.0.0"

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/api/generate",
        model: str = "llama-guard",
        timeout: float = 30.0,
    ):
        """
        Initialize LlamaGuard plugin.

        Args:
            endpoint: Ollama API endpoint or custom LlamaGuard API
            model: Model name (default: llama-guard)
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self._available = False

    def initialize(self) -> None:
        """Check if LlamaGuard is available."""
        # We'll check availability on first use
        pass

    async def _check_availability(self) -> bool:
        """Check if LlamaGuard endpoint is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(
                    self.endpoint.replace("/api/generate", "/api/tags")
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._available = any(
                        self.model in m or "llama-guard" in m.lower() for m in models
                    )
                    if not self._available:
                        logger.warning(
                            f"LlamaGuard model '{self.model}' not found. "
                            f"Available models: {models}. "
                            f"Install with: ollama pull llama-guard"
                        )
                    return self._available
        except Exception as e:
            logger.debug(f"LlamaGuard not available: {e}")
            self._available = False
        return False

    def _format_prompt(self, messages: list[dict]) -> str:
        """Format messages for LlamaGuard evaluation."""
        # LlamaGuard expects a specific format
        conversation = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                conversation.append(f"User: {content}")
            elif role == "assistant":
                conversation.append(f"Assistant: {content}")

        return "\n".join(conversation)

    def _parse_response(self, response_text: str) -> list[SecurityFinding]:
        """Parse LlamaGuard response into SecurityFindings."""
        findings = []
        response_lower = response_text.lower().strip()

        # LlamaGuard responds with "safe" or "unsafe\nS1,S2,..." format
        if response_lower.startswith("safe"):
            return findings

        if response_lower.startswith("unsafe"):
            # Extract categories
            lines = response_text.strip().split("\n")
            for line in lines[1:]:  # Skip "unsafe" line
                for code in line.split(","):
                    code = code.strip().upper()
                    if code in LLAMAGUARD_CATEGORIES:
                        category_name, severity = LLAMAGUARD_CATEGORIES[code]
                        findings.append(
                            SecurityFinding(
                                plugin=self.name,
                                category="content_safety",
                                severity=severity,
                                description=f"LlamaGuard: {category_name} ({code})",
                                pattern_matched=code,
                                confidence=0.9,  # ML-based detection
                                metadata={"llamaguard_category": code},
                            )
                        )

        return findings

    async def check_async(self, messages: list[dict]) -> list[SecurityFinding]:
        """
        Check messages using LlamaGuard.

        Args:
            messages: List of chat messages

        Returns:
            List of SecurityFinding objects
        """
        # Check availability on first use
        if not self._available:
            is_available = await self._check_availability()
            if not is_available:
                logger.debug("LlamaGuard not available, skipping check")
                return []

        prompt = self._format_prompt(messages)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    return self._parse_response(response_text)
                else:
                    logger.warning(f"LlamaGuard request failed: {response.status_code}")
                    return []

        except asyncio.TimeoutError:
            logger.warning("LlamaGuard request timed out")
            return []
        except Exception as e:
            logger.error(f"LlamaGuard error: {e}")
            return []


class OpenAIModerationPlugin(AsyncSecurityPlugin):
    """
    OpenAI Moderation API plugin.

    Alternative to LlamaGuard using OpenAI's moderation endpoint.
    Requires OpenAI API key.
    """

    name = "openai_moderation"
    description = "Content moderation using OpenAI Moderation API"
    version = "1.0.0"

    # OpenAI moderation categories
    CATEGORY_MAPPING = {
        "hate": ("Hate", RiskLevel.HIGH),
        "hate/threatening": ("Hate/Threatening", RiskLevel.CRITICAL),
        "harassment": ("Harassment", RiskLevel.HIGH),
        "harassment/threatening": ("Harassment/Threatening", RiskLevel.CRITICAL),
        "self-harm": ("Self-Harm", RiskLevel.CRITICAL),
        "self-harm/intent": ("Self-Harm Intent", RiskLevel.CRITICAL),
        "self-harm/instructions": ("Self-Harm Instructions", RiskLevel.CRITICAL),
        "sexual": ("Sexual Content", RiskLevel.HIGH),
        "sexual/minors": ("Sexual/Minors", RiskLevel.CRITICAL),
        "violence": ("Violence", RiskLevel.HIGH),
        "violence/graphic": ("Violence/Graphic", RiskLevel.CRITICAL),
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI Moderation plugin.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.api_key = api_key
        self._endpoint = "https://api.openai.com/v1/moderations"

    def initialize(self) -> None:
        if not self.api_key:
            import os

            self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning(
                "OpenAI Moderation plugin initialized without API key. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
            self.enabled = False

    async def check_async(self, messages: list[dict]) -> list[SecurityFinding]:
        """Check messages using OpenAI Moderation API."""
        if not self.api_key:
            return []

        findings = []

        # Combine all message content
        content = "\n".join(
            msg.get("content", "")
            for msg in messages
            if isinstance(msg.get("content"), str)
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": content},
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("results", [{}])[0]

                    if result.get("flagged"):
                        categories = result.get("categories", {})
                        scores = result.get("category_scores", {})

                        for category, flagged in categories.items():
                            if flagged:
                                category_info = self.CATEGORY_MAPPING.get(
                                    category, (category, RiskLevel.MEDIUM)
                                )
                                findings.append(
                                    SecurityFinding(
                                        plugin=self.name,
                                        category="content_safety",
                                        severity=category_info[1],
                                        description=f"OpenAI Moderation: {category_info[0]}",
                                        pattern_matched=category,
                                        confidence=scores.get(category, 0.5),
                                        metadata={"openai_category": category},
                                    )
                                )

        except Exception as e:
            logger.error(f"OpenAI Moderation error: {e}")

        return findings
