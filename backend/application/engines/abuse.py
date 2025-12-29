"""Abuse & Loop Detection Engine.

Detects and prevents:
- Request loops / recursion
- Retry storms
- Self-calling patterns
- Abnormal usage patterns
- Cost spikes

Uses Redis for distributed state storage.
"""

from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel
from enum import Enum
import hashlib
import json
import logging
import time

from backend.adapters.cache.redis_client import get_redis

logger = logging.getLogger(__name__)


class AbuseType(str, Enum):
    """Types of abuse detected."""

    LOOP_DETECTED = "loop_detected"
    RETRY_STORM = "retry_storm"
    RATE_SPIKE = "rate_spike"
    COST_SPIKE = "cost_spike"
    DUPLICATE_REQUEST = "duplicate_request"
    SELF_REFERENCE = "self_reference"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


class AbuseCheckResult(BaseModel):
    """Result of abuse detection check."""

    blocked: bool
    abuse_type: Optional[AbuseType] = None
    reason: Optional[str] = None
    details: dict = {}
    cooldown_seconds: Optional[int] = None


@dataclass
class RequestSignature:
    """Signature of a request for deduplication."""

    hash: str
    timestamp: float  # Unix timestamp for Redis
    app_id: str
    feature: str
    model: str
    input_hash: str


class AbuseDetector:
    """
    Detects abusive usage patterns using Redis for storage.

    Features:
    - Loop detection (same request repeated)
    - Retry storm detection (high error + retry rate)
    - Cost spike detection (sudden increase in costs)
    - Rate spike detection (sudden increase in requests)
    - Duplicate request detection
    """

    def __init__(
        self,
        max_identical_requests: int = 5,
        identical_request_window_seconds: int = 60,
        max_errors_per_minute: int = 20,
        error_window_seconds: int = 60,
        max_requests_per_minute: int = 100,
        rate_spike_multiplier: float = 5.0,
        cost_spike_multiplier: float = 10.0,
        dedup_window_seconds: int = 5,
    ):
        self.max_identical_requests = max_identical_requests
        self.identical_request_window_seconds = identical_request_window_seconds
        self.max_errors_per_minute = max_errors_per_minute
        self.error_window_seconds = error_window_seconds
        self.max_requests_per_minute = max_requests_per_minute
        self.rate_spike_multiplier = rate_spike_multiplier
        self.cost_spike_multiplier = cost_spike_multiplier
        self.dedup_window_seconds = dedup_window_seconds

        # Redis key prefixes
        self.SIGNATURES_KEY = "abuse:signatures:"
        self.REQUESTS_KEY = "abuse:requests:"
        self.ERRORS_KEY = "abuse:errors:"
        self.BLOCKED_KEY = "abuse:blocked:"
        self.COSTS_KEY = "abuse:costs:"
        self.STATS_KEY = "abuse:stats:"

    async def check_request(
        self,
        app_id: str,
        feature: str,
        model: str,
        messages: list[dict],
        request_id: Optional[str] = None,
    ) -> AbuseCheckResult:
        """Check if a request should be blocked for abuse."""
        now = time.time()

        # Check if currently blocked
        blocked_result = await self._check_blocked(app_id)
        if blocked_result:
            return blocked_result

        # Generate request signature
        signature = self._generate_signature(app_id, feature, model, messages)

        # Check for duplicate/loop
        loop_result = await self._check_loop(app_id, signature, now)
        if loop_result.blocked:
            await self._apply_cooldown(app_id, 30)
            return loop_result

        # Check rate spike
        rate_result = await self._check_rate_spike(app_id, now)
        if rate_result.blocked:
            await self._apply_cooldown(app_id, 60)
            return rate_result

        # Check for self-reference patterns
        self_ref_result = self._check_self_reference(messages)
        if self_ref_result.blocked:
            return self_ref_result

        # Record this request
        await self._record_request(app_id, signature, now)

        return AbuseCheckResult(blocked=False)

    async def record_error(self, app_id: str) -> AbuseCheckResult:
        """Record an error for retry storm detection."""
        redis = await get_redis()
        if not redis:
            return AbuseCheckResult(blocked=False)

        now = time.time()
        key = f"{self.ERRORS_KEY}{app_id}"

        try:
            # Add error timestamp with score
            await redis.zadd(key, {str(now): now})

            # Remove old errors outside window
            cutoff = now - self.error_window_seconds
            await redis.zremrangebyscore(key, 0, cutoff)

            # Set TTL
            await redis.expire(key, self.error_window_seconds * 2)

            # Count errors in window
            error_count = await redis.zcard(key)

            if error_count > self.max_errors_per_minute:
                await self._apply_cooldown(app_id, 120)
                return AbuseCheckResult(
                    blocked=True,
                    abuse_type=AbuseType.RETRY_STORM,
                    reason=f"Too many errors ({error_count}) in {self.error_window_seconds}s window",
                    details={"error_count": error_count},
                    cooldown_seconds=120,
                )
        except Exception as e:
            logger.warning(f"Redis error in record_error: {e}")

        return AbuseCheckResult(blocked=False)

    async def record_cost(self, app_id: str, cost: float) -> AbuseCheckResult:
        """Record a cost for cost spike detection."""
        redis = await get_redis()
        if not redis:
            return AbuseCheckResult(blocked=False)

        key = f"{self.COSTS_KEY}{app_id}"
        stats_key = f"{self.STATS_KEY}{app_id}"

        try:
            # Add cost to list
            await redis.rpush(key, str(cost))
            # Keep only last 100 costs
            await redis.ltrim(key, -100, -1)
            await redis.expire(key, 3600)  # 1 hour TTL

            # Update total cost
            await redis.hincrbyfloat(stats_key, "total_cost", cost)

            # Get all costs for spike detection
            costs_raw = await redis.lrange(key, 0, -1)
            costs = [float(c) for c in costs_raw]

            if len(costs) >= 10:
                avg_cost = sum(costs[:-1]) / (len(costs) - 1)
                if cost > avg_cost * self.cost_spike_multiplier and avg_cost > 0.001:
                    return AbuseCheckResult(
                        blocked=False,  # Warning only
                        abuse_type=AbuseType.COST_SPIKE,
                        reason=f"Cost spike detected: ${cost:.4f} vs avg ${avg_cost:.4f}",
                        details={
                            "current_cost": cost,
                            "average_cost": avg_cost,
                            "multiplier": cost / avg_cost if avg_cost > 0 else 0,
                        },
                    )
        except Exception as e:
            logger.warning(f"Redis error in record_cost: {e}")

        return AbuseCheckResult(blocked=False)

    async def _check_blocked(self, app_id: str) -> Optional[AbuseCheckResult]:
        """Check if app is currently blocked."""
        redis = await get_redis()
        if not redis:
            return None

        try:
            blocked_until = await redis.get(f"{self.BLOCKED_KEY}{app_id}")
            if blocked_until:
                blocked_ts = float(blocked_until)
                now = time.time()
                if now < blocked_ts:
                    remaining = int(blocked_ts - now)
                    return AbuseCheckResult(
                        blocked=True,
                        abuse_type=AbuseType.SUSPICIOUS_PATTERN,
                        reason=f"Application temporarily blocked for {remaining}s",
                        cooldown_seconds=remaining,
                    )
                else:
                    # Block expired, remove it
                    await redis.delete(f"{self.BLOCKED_KEY}{app_id}")
        except Exception as e:
            logger.warning(f"Redis error in _check_blocked: {e}")

        return None

    async def _check_loop(
        self,
        app_id: str,
        signature: RequestSignature,
        now: float,
    ) -> AbuseCheckResult:
        """Check for request loops using Redis sorted sets."""
        redis = await get_redis()
        if not redis:
            return AbuseCheckResult(blocked=False)

        key = f"{self.SIGNATURES_KEY}{app_id}:{signature.input_hash}"

        try:
            # Remove old signatures outside window
            cutoff = now - self.identical_request_window_seconds
            await redis.zremrangebyscore(key, 0, cutoff)

            # Count identical requests in window
            identical_count = await redis.zcard(key)

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
            recent_count = await redis.zcount(key, dedup_cutoff, now)

            if recent_count > 0:
                return AbuseCheckResult(
                    blocked=True,
                    abuse_type=AbuseType.DUPLICATE_REQUEST,
                    reason=f"Duplicate request within {self.dedup_window_seconds}s",
                    details={"dedup_window": self.dedup_window_seconds},
                    cooldown_seconds=5,
                )
        except Exception as e:
            logger.warning(f"Redis error in _check_loop: {e}")

        return AbuseCheckResult(blocked=False)

    async def _check_rate_spike(self, app_id: str, now: float) -> AbuseCheckResult:
        """Check for sudden rate increase."""
        redis = await get_redis()
        if not redis:
            return AbuseCheckResult(blocked=False)

        key = f"{self.REQUESTS_KEY}{app_id}"

        try:
            # Count requests in last minute
            minute_ago = now - 60
            recent_count = await redis.zcount(key, minute_ago, now)

            # Check absolute limit
            if recent_count > self.max_requests_per_minute:
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

            # Check for spike vs historical average (last 10 minutes)
            total_count = await redis.zcard(key)
            if total_count >= 50:
                ten_minutes_ago = now - 600
                historical_count = await redis.zcount(key, ten_minutes_ago, now)
                historical_rate = historical_count / 10  # per minute average

                if (
                    historical_rate > 0
                    and recent_count > historical_rate * self.rate_spike_multiplier
                ):
                    return AbuseCheckResult(
                        blocked=True,
                        abuse_type=AbuseType.RATE_SPIKE,
                        reason=f"Sudden rate spike: {recent_count}/min vs avg {historical_rate:.1f}/min",
                        details={
                            "current_rate": recent_count,
                            "average_rate": historical_rate,
                            "multiplier": recent_count / historical_rate,
                        },
                        cooldown_seconds=60,
                    )
        except Exception as e:
            logger.warning(f"Redis error in _check_rate_spike: {e}")

        return AbuseCheckResult(blocked=False)

    def _check_self_reference(self, messages: list[dict]) -> AbuseCheckResult:
        """Check for self-referencing patterns that might indicate loops."""
        suspicious_patterns = [
            "call yourself",
            "repeat this request",
            "call this api again",
            "infinite loop",
            "keep calling",
            "recursive call",
        ]

        for msg in messages:
            content = msg.get("content", "").lower()
            for pattern in suspicious_patterns:
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
        """Generate a signature for a request."""
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

    async def _record_request(
        self,
        app_id: str,
        signature: RequestSignature,
        now: float,
    ) -> None:
        """Record a request signature in Redis."""
        redis = await get_redis()
        if not redis:
            return

        try:
            # Record signature for loop detection
            sig_key = f"{self.SIGNATURES_KEY}{app_id}:{signature.input_hash}"
            await redis.zadd(sig_key, {signature.hash: now})
            await redis.expire(sig_key, self.identical_request_window_seconds * 2)

            # Record request for rate limiting
            req_key = f"{self.REQUESTS_KEY}{app_id}"
            await redis.zadd(req_key, {f"{now}:{signature.hash}": now})
            # Keep only last 10 minutes of requests
            cutoff = now - 600
            await redis.zremrangebyscore(req_key, 0, cutoff)
            await redis.expire(req_key, 700)

            # Update stats
            stats_key = f"{self.STATS_KEY}{app_id}"
            await redis.hincrby(stats_key, "request_count", 1)
            await redis.hset(stats_key, "last_request", str(now))
            await redis.expire(stats_key, 86400)  # 24 hours
        except Exception as e:
            logger.warning(f"Redis error in _record_request: {e}")

    async def _apply_cooldown(self, app_id: str, seconds: int) -> None:
        """Apply a cooldown to an application."""
        redis = await get_redis()
        if not redis:
            return

        try:
            blocked_until = time.time() + seconds
            await redis.setex(f"{self.BLOCKED_KEY}{app_id}", seconds, str(blocked_until))
        except Exception as e:
            logger.warning(f"Redis error in _apply_cooldown: {e}")

    async def get_app_stats(self, app_id: str) -> dict:
        """Get statistics for an application."""
        redis = await get_redis()
        if not redis:
            return {}

        try:
            stats_key = f"{self.STATS_KEY}{app_id}"
            req_key = f"{self.REQUESTS_KEY}{app_id}"

            stats = await redis.hgetall(stats_key)
            now = time.time()
            minute_ago = now - 60

            recent_count = await redis.zcount(req_key, minute_ago, now)
            is_blocked = await redis.exists(f"{self.BLOCKED_KEY}{app_id}")
            blocked_until_raw = await redis.get(f"{self.BLOCKED_KEY}{app_id}")

            return {
                "total_requests": int(stats.get("request_count", 0)),
                "requests_last_minute": recent_count,
                "total_cost": float(stats.get("total_cost", 0)),
                "last_request": stats.get("last_request"),
                "is_blocked": bool(is_blocked),
                "blocked_until": float(blocked_until_raw) if blocked_until_raw else None,
            }
        except Exception as e:
            logger.warning(f"Redis error in get_app_stats: {e}")
            return {}

    async def clear_app_data(self, app_id: str) -> None:
        """Clear all data for an application."""
        redis = await get_redis()
        if not redis:
            return

        try:
            # Find and delete all keys for this app
            patterns = [
                f"{self.SIGNATURES_KEY}{app_id}:*",
                f"{self.REQUESTS_KEY}{app_id}",
                f"{self.ERRORS_KEY}{app_id}",
                f"{self.COSTS_KEY}{app_id}",
                f"{self.STATS_KEY}{app_id}",
                f"{self.BLOCKED_KEY}{app_id}",
            ]

            for pattern in patterns:
                if "*" in pattern:
                    keys = []
                    async for key in redis.scan_iter(pattern):
                        keys.append(key)
                    if keys:
                        await redis.delete(*keys)
                else:
                    await redis.delete(pattern)
        except Exception as e:
            logger.warning(f"Redis error in clear_app_data: {e}")


# Singleton instance
abuse_detector = AbuseDetector()
