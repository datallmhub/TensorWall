"""InMemory Abuse Adapter - Implémentation native pour les tests.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface AbuseDetectorPort sans dépendre de Redis.
Utile pour les tests unitaires et d'intégration.
"""

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import time

from backend.ports.abuse_detector import (
    AbuseDetectorPort,
    AbuseCheckResult,
    AbuseType,
)


@dataclass
class RequestSignature:
    """Signature d'une requête pour la déduplication."""

    hash: str
    timestamp: float
    app_id: str
    feature: str
    model: str
    input_hash: str


class InMemoryAbuseAdapter(AbuseDetectorPort):
    """Adapter en mémoire pour la détection d'abus.

    Implémentation sans Redis pour les tests. Stocke tout en mémoire.
    Configurable pour simuler différents scénarios de blocage.
    """

    # Patterns suspects dans le contenu
    SUSPICIOUS_PATTERNS = [
        "call yourself",
        "repeat this request",
        "call this api again",
        "infinite loop",
        "keep calling",
        "recursive call",
    ]

    def __init__(
        self,
        max_identical_requests: int = 5,
        identical_request_window_seconds: int = 60,
        max_errors_per_minute: int = 20,
        max_requests_per_minute: int = 100,
        dedup_window_seconds: int = 5,
        cost_spike_multiplier: float = 10.0,
    ):
        """Initialise l'adapter.

        Args:
            max_identical_requests: Nombre max de requêtes identiques
            identical_request_window_seconds: Fenêtre pour les requêtes identiques
            max_errors_per_minute: Nombre max d'erreurs par minute
            max_requests_per_minute: Nombre max de requêtes par minute
            dedup_window_seconds: Fenêtre de déduplication
            cost_spike_multiplier: Multiplicateur pour détecter les spikes de coût
        """
        self.max_identical_requests = max_identical_requests
        self.identical_request_window_seconds = identical_request_window_seconds
        self.max_errors_per_minute = max_errors_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        self.dedup_window_seconds = dedup_window_seconds
        self.cost_spike_multiplier = cost_spike_multiplier

        # Storage
        self._signatures: dict[str, list[tuple[float, str]]] = defaultdict(list)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._errors: dict[str, list[float]] = defaultdict(list)
        self._costs: dict[str, list[float]] = defaultdict(list)
        self._blocked_until: dict[str, float] = {}

        # Configurable blocks for testing
        self._force_block: dict[str, AbuseCheckResult] = {}

    def configure_block(self, app_id: str, result: AbuseCheckResult) -> None:
        """Configure un blocage forcé pour les tests.

        Args:
            app_id: Identifiant de l'application
            result: Résultat à retourner (doit avoir blocked=True)
        """
        if result.blocked:
            self._force_block[app_id] = result

    def clear_forced_blocks(self) -> None:
        """Efface tous les blocages forcés."""
        self._force_block.clear()

    async def check_request(
        self,
        app_id: str,
        feature: str,
        model: str,
        messages: list[dict],
        request_id: str | None = None,
    ) -> AbuseCheckResult:
        """Vérifie si une requête doit être bloquée pour abus."""
        now = time.time()

        # Check forced block (for testing)
        if app_id in self._force_block:
            return self._force_block[app_id]

        # Check if currently blocked
        blocked_result = self._check_blocked(app_id, now)
        if blocked_result:
            return blocked_result

        # Generate request signature
        signature = self._generate_signature(app_id, feature, model, messages)

        # Check for duplicate/loop
        loop_result = self._check_loop(app_id, signature, now)
        if loop_result.blocked:
            self._apply_cooldown(app_id, 30, now)
            return loop_result

        # Check rate spike
        rate_result = self._check_rate_spike(app_id, now)
        if rate_result.blocked:
            self._apply_cooldown(app_id, 60, now)
            return rate_result

        # Check for self-reference patterns
        self_ref_result = self._check_self_reference(messages)
        if self_ref_result.blocked:
            return self_ref_result

        # Record this request
        self._record_request(app_id, signature, now)

        return AbuseCheckResult(blocked=False)

    async def record_error(self, app_id: str) -> AbuseCheckResult:
        """Enregistre une erreur pour la détection de retry storm."""
        now = time.time()

        # Add error timestamp
        self._errors[app_id].append(now)

        # Remove old errors
        cutoff = now - 60  # 1 minute window
        self._errors[app_id] = [t for t in self._errors[app_id] if t > cutoff]

        # Check if too many errors
        error_count = len(self._errors[app_id])
        if error_count > self.max_errors_per_minute:
            self._apply_cooldown(app_id, 120, now)
            return AbuseCheckResult(
                blocked=True,
                abuse_type=AbuseType.RETRY_STORM,
                reason=f"Too many errors ({error_count}) in 60s window",
                details={"error_count": error_count},
                cooldown_seconds=120,
            )

        return AbuseCheckResult(blocked=False)

    async def record_cost(self, app_id: str, cost: float) -> AbuseCheckResult:
        """Enregistre un coût pour la détection de cost spike."""
        self._costs[app_id].append(cost)

        # Keep only last 100 costs
        if len(self._costs[app_id]) > 100:
            self._costs[app_id] = self._costs[app_id][-100:]

        costs = self._costs[app_id]
        if len(costs) >= 10:
            avg_cost = sum(costs[:-1]) / (len(costs) - 1)
            if cost > avg_cost * self.cost_spike_multiplier and avg_cost > 0.001:
                return AbuseCheckResult(
                    blocked=False,  # Warning only, not blocking
                    abuse_type=AbuseType.COST_SPIKE,
                    reason=f"Cost spike detected: ${cost:.4f} vs avg ${avg_cost:.4f}",
                    details={
                        "current_cost": cost,
                        "average_cost": avg_cost,
                        "multiplier": cost / avg_cost if avg_cost > 0 else 0,
                    },
                )

        return AbuseCheckResult(blocked=False)

    async def clear_app_data(self, app_id: str) -> None:
        """Efface toutes les données d'une application."""
        self._signatures.pop(app_id, None)
        self._requests.pop(app_id, None)
        self._errors.pop(app_id, None)
        self._costs.pop(app_id, None)
        self._blocked_until.pop(app_id, None)
        self._force_block.pop(app_id, None)

        # Also clear signature keys that start with app_id
        keys_to_remove = [k for k in self._signatures.keys() if k.startswith(f"{app_id}:")]
        for key in keys_to_remove:
            del self._signatures[key]

    def clear_all(self) -> None:
        """Efface toutes les données (pour les tests)."""
        self._signatures.clear()
        self._requests.clear()
        self._errors.clear()
        self._costs.clear()
        self._blocked_until.clear()
        self._force_block.clear()

    def _check_blocked(self, app_id: str, now: float) -> AbuseCheckResult | None:
        """Vérifie si l'application est actuellement bloquée."""
        if app_id in self._blocked_until:
            blocked_until = self._blocked_until[app_id]
            if now < blocked_until:
                remaining = int(blocked_until - now)
                return AbuseCheckResult(
                    blocked=True,
                    abuse_type=AbuseType.SUSPICIOUS_PATTERN,
                    reason=f"Application temporarily blocked for {remaining}s",
                    cooldown_seconds=remaining,
                )
            else:
                # Block expired
                del self._blocked_until[app_id]
        return None

    def _check_loop(
        self,
        app_id: str,
        signature: RequestSignature,
        now: float,
    ) -> AbuseCheckResult:
        """Vérifie les boucles de requêtes."""
        key = f"{app_id}:{signature.input_hash}"

        # Remove old signatures
        cutoff = now - self.identical_request_window_seconds
        self._signatures[key] = [(ts, h) for ts, h in self._signatures[key] if ts > cutoff]

        # Count identical requests
        identical_count = len(self._signatures[key])

        if identical_count >= self.max_identical_requests:
            return AbuseCheckResult(
                blocked=True,
                abuse_type=AbuseType.LOOP_DETECTED,
                reason=f"Identical request repeated {identical_count} times",
                details={
                    "identical_count": identical_count,
                    "window_seconds": self.identical_request_window_seconds,
                },
                cooldown_seconds=30,
            )

        # Check for exact duplicates in short window
        dedup_cutoff = now - self.dedup_window_seconds
        recent = [ts for ts, _ in self._signatures[key] if ts > dedup_cutoff]

        if len(recent) > 0:
            return AbuseCheckResult(
                blocked=True,
                abuse_type=AbuseType.DUPLICATE_REQUEST,
                reason=f"Duplicate request within {self.dedup_window_seconds}s",
                details={"dedup_window": self.dedup_window_seconds},
                cooldown_seconds=5,
            )

        return AbuseCheckResult(blocked=False)

    def _check_rate_spike(self, app_id: str, now: float) -> AbuseCheckResult:
        """Vérifie les augmentations soudaines de trafic."""
        # Remove old requests
        minute_ago = now - 60
        self._requests[app_id] = [t for t in self._requests[app_id] if t > minute_ago]

        recent_count = len(self._requests[app_id])

        # Use >= because the current request hasn't been recorded yet
        if recent_count >= self.max_requests_per_minute:
            return AbuseCheckResult(
                blocked=True,
                abuse_type=AbuseType.RATE_SPIKE,
                reason=f"Rate limit exceeded: {recent_count}/min > {self.max_requests_per_minute}/min",
                details={
                    "current_rate": recent_count,
                    "limit": self.max_requests_per_minute,
                },
                cooldown_seconds=60,
            )

        return AbuseCheckResult(blocked=False)

    def _check_self_reference(self, messages: list[dict]) -> AbuseCheckResult:
        """Vérifie les patterns de self-référence."""
        for msg in messages:
            content = msg.get("content", "").lower()
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern in content:
                    return AbuseCheckResult(
                        blocked=True,
                        abuse_type=AbuseType.SELF_REFERENCE,
                        reason=f"Self-referencing pattern detected: '{pattern}'",
                        details={"pattern": pattern},
                    )

        return AbuseCheckResult(blocked=False)

    def _generate_signature(
        self,
        app_id: str,
        feature: str,
        model: str,
        messages: list[dict],
    ) -> RequestSignature:
        """Génère une signature pour une requête."""
        content = json.dumps(messages, sort_keys=True)
        input_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        full_hash = hashlib.sha256(f"{app_id}:{feature}:{model}:{input_hash}".encode()).hexdigest()[
            :16
        ]

        return RequestSignature(
            hash=full_hash,
            timestamp=time.time(),
            app_id=app_id,
            feature=feature,
            model=model,
            input_hash=input_hash,
        )

    def _record_request(
        self,
        app_id: str,
        signature: RequestSignature,
        now: float,
    ) -> None:
        """Enregistre une requête."""
        # Record signature
        key = f"{app_id}:{signature.input_hash}"
        self._signatures[key].append((now, signature.hash))

        # Record request timestamp
        self._requests[app_id].append(now)

    def _apply_cooldown(self, app_id: str, seconds: int, now: float) -> None:
        """Applique un cooldown à une application."""
        self._blocked_until[app_id] = now + seconds

    # Test helpers
    def get_request_count(self, app_id: str) -> int:
        """Retourne le nombre de requêtes enregistrées."""
        return len(self._requests.get(app_id, []))

    def get_error_count(self, app_id: str) -> int:
        """Retourne le nombre d'erreurs enregistrées."""
        return len(self._errors.get(app_id, []))

    def is_blocked(self, app_id: str) -> bool:
        """Vérifie si l'application est bloquée."""
        if app_id in self._blocked_until:
            return time.time() < self._blocked_until[app_id]
        return app_id in self._force_block
