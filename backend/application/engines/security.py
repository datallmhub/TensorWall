"""
LLM Security Guard

Built-in security detection for LLM requests:
- Prompt injection detection (OWASP LLM01)
- PII/secrets detection (OWASP LLM06)
- Abuse pattern detection
- Risk scoring (0.0 - 1.0)

All detections are logged and visible in API responses.
"""

from pydantic import BaseModel
from enum import Enum
import re
from typing import Optional


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityFinding(BaseModel):
    """Individual security finding."""

    category: str  # "prompt_injection", "pii", "secrets", "abuse"
    severity: RiskLevel
    description: str
    pattern_matched: Optional[str] = None


class SecurityCheckResult(BaseModel):
    """Result of security analysis."""

    safe: bool
    risk_level: str  # low, medium, high, critical
    risk_score: float  # 0.0 - 1.0 for fine-grained scoring
    issues: list[str] = []
    findings: list[SecurityFinding] = []

    def to_api_response(self) -> dict:
        """Format for API response (visible in every request)."""
        return {
            "safe": self.safe,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "issues_count": len(self.issues),
            "findings": (
                [
                    {
                        "category": f.category,
                        "severity": f.severity.value,
                        "description": f.description,
                    }
                    for f in self.findings
                ]
                if self.findings
                else []
            ),
        }


class SecurityGuard:
    """
    LLM Security Guard - Detects security threats in LLM requests.

    Detections included:
    - Prompt injection (13 patterns) - OWASP LLM01
    - PII detection (email, phone, SSN, credit cards) - OWASP LLM06
    - Secrets detection (API keys, passwords, tokens) - OWASP LLM06
    """

    # Prompt injection patterns (OWASP LLM01)
    INJECTION_PATTERNS = [
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
        (r"###\s*instruction", "delimiter_injection"),
        (r"ignore\s+safety", "safety_bypass"),
        (r"bypass\s+(filter|safety|restriction)", "safety_bypass"),
    ]

    # Secrets & credentials patterns (OWASP LLM06)
    SECRETS_PATTERNS = [
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+", "password"),
        (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+", "api_key"),
        (r"(?i)(secret|token)\s*[:=]\s*\S+", "secret_token"),
        (r"sk-[a-zA-Z0-9]{20,}", "openai_api_key"),
        (r"(?i)bearer\s+[a-zA-Z0-9\-_.]{20,}", "bearer_token"),
        (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "private_key"),
        (r"(?i)(aws_access_key_id|aws_secret)\s*[:=]\s*\S+", "aws_credential"),
        (r"ghp_[a-zA-Z0-9]{36}", "github_token"),
        (r"xox[baprs]-[a-zA-Z0-9-]+", "slack_token"),
    ]

    # PII patterns (OWASP LLM06)
    PII_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone_number"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit_card"),
    ]

    def __init__(self):
        """Initialize SecurityGuard with compiled regex patterns."""
        self.injection_regex = [
            (re.compile(p, re.IGNORECASE), name) for p, name in self.INJECTION_PATTERNS
        ]
        self.secrets_regex = [
            (re.compile(p), name) for p, name in self.SECRETS_PATTERNS
        ]
        self.pii_regex = [(re.compile(p), name) for p, name in self.PII_PATTERNS]

    def check_prompt(self, messages: list[dict]) -> SecurityCheckResult:
        """
        Analyze messages for security threats.

        Returns SecurityCheckResult with:
        - risk_level: low/medium/high/critical
        - risk_score: 0.0-1.0
        - findings: detailed security findings
        """
        findings: list[SecurityFinding] = []
        issues: list[str] = []
        max_risk = RiskLevel.LOW

        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            role = msg.get("role", "user")

            # 1. Check prompt injection (only user messages)
            if role == "user":
                for pattern, pattern_name in self.injection_regex:
                    if pattern.search(content):
                        finding = SecurityFinding(
                            category="prompt_injection",
                            severity=RiskLevel.HIGH,
                            description=f"Potential prompt injection: {pattern_name}",
                            pattern_matched=pattern_name,
                        )
                        findings.append(finding)
                        issues.append(f"Prompt injection detected: {pattern_name}")
                        max_risk = RiskLevel.HIGH

            # 2. Check secrets (all messages)
            for pattern, secret_type in self.secrets_regex:
                if pattern.search(content):
                    finding = SecurityFinding(
                        category="secrets",
                        severity=RiskLevel.HIGH,
                        description=f"Potential {secret_type} detected in prompt",
                        pattern_matched=secret_type,
                    )
                    findings.append(finding)
                    issues.append(f"Secret detected: {secret_type}")
                    if max_risk.value < RiskLevel.HIGH.value:
                        max_risk = RiskLevel.HIGH

            # 3. Check PII (all messages)
            for pattern, pii_type in self.pii_regex:
                if pattern.search(content):
                    finding = SecurityFinding(
                        category="pii",
                        severity=RiskLevel.MEDIUM,
                        description=f"Potential {pii_type} detected in prompt",
                        pattern_matched=pii_type,
                    )
                    findings.append(finding)
                    issues.append(f"PII detected: {pii_type}")
                    if max_risk == RiskLevel.LOW:
                        max_risk = RiskLevel.MEDIUM

        # Calculate risk score (0.0 - 1.0)
        risk_score = self._calculate_risk_score(findings)

        return SecurityCheckResult(
            safe=len(findings) == 0,
            risk_level=max_risk.value,
            risk_score=risk_score,
            issues=issues,
            findings=findings,
        )

    def _calculate_risk_score(self, findings: list[SecurityFinding]) -> float:
        """Calculate aggregate risk score from findings."""
        if not findings:
            return 0.0

        # Weight by severity
        weights = {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.3,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 1.0,
        }

        total_weight = sum(weights.get(f.severity, 0.1) for f in findings)
        # Normalize to 0-1 range, cap at 1.0
        score = min(total_weight / 2.0, 1.0)
        return round(score, 2)

    def check_message_structure(self, messages: list[dict]) -> SecurityCheckResult:
        """
        Validate message structure.
        Checks: valid roles, single system message, non-empty content.
        """
        findings: list[SecurityFinding] = []
        issues: list[str] = []

        if not messages:
            return SecurityCheckResult(
                safe=False,
                risk_level=RiskLevel.MEDIUM.value,
                risk_score=0.3,
                issues=["Empty messages array"],
                findings=[
                    SecurityFinding(
                        category="validation",
                        severity=RiskLevel.MEDIUM,
                        description="Empty messages array",
                    )
                ],
            )

        valid_roles = {"system", "user", "assistant", "tool", "function"}
        seen_system = False

        for i, msg in enumerate(messages):
            role = msg.get("role")

            if role not in valid_roles:
                issues.append(f"Invalid role at index {i}: {role}")
                findings.append(
                    SecurityFinding(
                        category="validation",
                        severity=RiskLevel.MEDIUM,
                        description=f"Invalid role: {role}",
                    )
                )

            if role == "system":
                if seen_system:
                    issues.append("Multiple system messages detected")
                    findings.append(
                        SecurityFinding(
                            category="validation",
                            severity=RiskLevel.LOW,
                            description="Multiple system messages",
                        )
                    )
                if i != 0:
                    issues.append("System message should be first")
                    findings.append(
                        SecurityFinding(
                            category="validation",
                            severity=RiskLevel.LOW,
                            description="System message not first",
                        )
                    )
                seen_system = True

            if not msg.get("content") and role not in ["tool", "function"]:
                issues.append(f"Empty content at index {i}")

        risk_score = self._calculate_risk_score(findings)

        return SecurityCheckResult(
            safe=len(issues) == 0,
            risk_level=RiskLevel.MEDIUM.value if issues else RiskLevel.LOW.value,
            risk_score=risk_score,
            issues=issues,
            findings=findings,
        )

    def full_analysis(self, messages: list[dict]) -> SecurityCheckResult:
        """
        Run complete security analysis.
        Combines prompt check + structure validation.
        """
        prompt_result = self.check_prompt(messages)
        structure_result = self.check_message_structure(messages)

        # Merge results
        all_findings = prompt_result.findings + structure_result.findings
        all_issues = prompt_result.issues + structure_result.issues

        # Take highest risk
        risk_levels = [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        prompt_risk_idx = risk_levels.index(RiskLevel(prompt_result.risk_level))
        struct_risk_idx = risk_levels.index(RiskLevel(structure_result.risk_level))
        max_risk = risk_levels[max(prompt_risk_idx, struct_risk_idx)]

        return SecurityCheckResult(
            safe=prompt_result.safe and structure_result.safe,
            risk_level=max_risk.value,
            risk_score=max(prompt_result.risk_score, structure_result.risk_score),
            issues=all_issues,
            findings=all_findings,
        )


# Default singleton
security_guard = SecurityGuard()
