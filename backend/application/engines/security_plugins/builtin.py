"""
Built-in Security Plugins

Default plugins that ship with TensorWall.
"""

import re

from backend.application.engines.security_plugins.base import (
    SecurityPlugin,
    SecurityFinding,
    RiskLevel,
)


class PromptInjectionPlugin(SecurityPlugin):
    """
    Detects prompt injection attacks.

    Covers OWASP LLM01: Prompt Injection
    - Instruction override attempts
    - Role hijacking
    - System prompt injection
    - Token injection
    - Safety bypass attempts
    """

    name = "prompt_injection"
    description = "Detects prompt injection attacks (OWASP LLM01)"
    version = "1.0.0"

    PATTERNS = [
        (r"ignore\s+(previous|all|above)\s+instructions", "instruction_override"),
        (r"disregard\s+(previous|all|above)", "instruction_override"),
        (r"forget\s+(everything|all|previous)", "memory_manipulation"),
        (r"you\s+are\s+now\s+", "role_hijacking"),
        (r"pretend\s+(you're|to\s+be)", "role_hijacking"),
        (r"act\s+as\s+(if|a)", "role_hijacking"),
        (r"new\s+instructions?:", "instruction_injection"),
        (r"system\s*:\s*", "system_prompt_injection"),
        (r"\[system\]", "system_prompt_injection"),
        (r"<\|im_start\|>", "token_injection"),
        (r"<\|endoftext\|>", "token_injection"),
        (r"###\s*instruction", "delimiter_injection"),
        (r"ignore\s+safety", "safety_bypass"),
        (r"bypass\s+(filter|safety|restriction)", "safety_bypass"),
        (r"jailbreak", "jailbreak_attempt"),
        (r"DAN\s*mode", "jailbreak_attempt"),
        (r"developer\s+mode", "jailbreak_attempt"),
    ]

    def initialize(self) -> None:
        self._compiled = [
            (re.compile(p, re.IGNORECASE), name)
            for p, name in self.PATTERNS
        ]

    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        findings = []

        for msg in messages:
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            for pattern, pattern_name in self._compiled:
                if pattern.search(content):
                    findings.append(SecurityFinding(
                        plugin=self.name,
                        category="prompt_injection",
                        severity=RiskLevel.HIGH,
                        description=f"Potential prompt injection: {pattern_name}",
                        pattern_matched=pattern_name,
                    ))

        return findings


class SecretsPlugin(SecurityPlugin):
    """
    Detects secrets and credentials in prompts.

    Covers OWASP LLM06: Sensitive Information Disclosure
    """

    name = "secrets"
    description = "Detects API keys, passwords, and credentials"
    version = "1.0.0"

    PATTERNS = [
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+", "password"),
        (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+", "api_key"),
        (r"(?i)(secret|token)\s*[:=]\s*\S+", "secret_token"),
        (r"sk-[a-zA-Z0-9]{20,}", "openai_api_key"),
        (r"(?i)bearer\s+[a-zA-Z0-9\-_.]{20,}", "bearer_token"),
        (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "private_key"),
        (r"(?i)(aws_access_key_id|aws_secret)\s*[:=]\s*\S+", "aws_credential"),
        (r"ghp_[a-zA-Z0-9]{36}", "github_token"),
        (r"gho_[a-zA-Z0-9]{36}", "github_oauth_token"),
        (r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}", "github_pat"),
        (r"xox[baprs]-[a-zA-Z0-9-]+", "slack_token"),
        (r"(?i)AKIA[0-9A-Z]{16}", "aws_access_key"),
        (r"(?i)(mysql|postgres|mongodb)://[^:]+:[^@]+@", "database_url"),
    ]

    def initialize(self) -> None:
        self._compiled = [
            (re.compile(p), name)
            for p, name in self.PATTERNS
        ]

    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        findings = []

        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            for pattern, secret_type in self._compiled:
                if pattern.search(content):
                    findings.append(SecurityFinding(
                        plugin=self.name,
                        category="secrets",
                        severity=RiskLevel.HIGH,
                        description=f"Potential {secret_type} detected",
                        pattern_matched=secret_type,
                    ))

        return findings


class PIIPlugin(SecurityPlugin):
    """
    Detects Personally Identifiable Information.

    Covers OWASP LLM06: Sensitive Information Disclosure
    """

    name = "pii"
    description = "Detects emails, phone numbers, SSN, credit cards"
    version = "1.0.0"

    PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone_number"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit_card"),
        (r"\b\d{9}\b", "potential_ssn"),  # 9 digits without dashes
    ]

    def initialize(self) -> None:
        self._compiled = [
            (re.compile(p), name)
            for p, name in self.PATTERNS
        ]

    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        findings = []

        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            for pattern, pii_type in self._compiled:
                if pattern.search(content):
                    findings.append(SecurityFinding(
                        plugin=self.name,
                        category="pii",
                        severity=RiskLevel.MEDIUM,
                        description=f"Potential {pii_type} detected",
                        pattern_matched=pii_type,
                    ))

        return findings


class CodeInjectionPlugin(SecurityPlugin):
    """
    Detects potential code injection in prompts.

    Looks for shell commands, SQL, and other executable code.
    """

    name = "code_injection"
    description = "Detects shell commands and SQL injection patterns"
    version = "1.0.0"

    PATTERNS = [
        # Shell commands
        (r";\s*(rm|chmod|chown|wget|curl|bash|sh|nc|netcat)\s", "shell_command"),
        (r"\|\s*(bash|sh|python|perl|ruby)\b", "pipe_to_shell"),
        (r"`[^`]*`", "backtick_execution"),
        (r"\$\([^)]+\)", "command_substitution"),
        # SQL injection
        (r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)", "sql_injection"),
        (r"(?i)('\s*or\s*'1'\s*=\s*'1|--\s*$)", "sql_injection"),
        # Path traversal
        (r"\.\./\.\.", "path_traversal"),
    ]

    def initialize(self) -> None:
        self._compiled = [
            (re.compile(p), name)
            for p, name in self.PATTERNS
        ]

    def check(self, messages: list[dict]) -> list[SecurityFinding]:
        findings = []

        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            for pattern, attack_type in self._compiled:
                if pattern.search(content):
                    findings.append(SecurityFinding(
                        plugin=self.name,
                        category="code_injection",
                        severity=RiskLevel.HIGH,
                        description=f"Potential {attack_type} detected",
                        pattern_matched=attack_type,
                    ))

        return findings


def register_builtin_plugins(manager) -> None:
    """Register all built-in plugins with the manager."""
    plugins = [
        PromptInjectionPlugin(),
        SecretsPlugin(),
        PIIPlugin(),
        CodeInjectionPlugin(),
    ]

    for plugin in plugins:
        plugin.initialize()
        manager.register(plugin)
