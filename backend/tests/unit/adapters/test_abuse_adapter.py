"""Tests unitaires pour l'adapter de détection d'abus.

Ces tests vérifient que InMemoryAbuseAdapter implémente correctement
l'interface AbuseDetectorPort.
"""

import pytest
import time

from backend.adapters.abuse import InMemoryAbuseAdapter
from backend.ports.abuse_detector import AbuseDetectorPort, AbuseCheckResult, AbuseType


# =============================================================================
# Tests InMemoryAbuseAdapter - Basic
# =============================================================================


class TestInMemoryAbuseAdapter:
    """Tests pour l'adapter InMemory."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = InMemoryAbuseAdapter()
        assert isinstance(adapter, AbuseDetectorPort)

    @pytest.mark.asyncio
    async def test_first_request_not_blocked(self):
        """Vérifie qu'une première requête n'est pas bloquée."""
        adapter = InMemoryAbuseAdapter()
        result = await adapter.check_request(
            app_id="app-1",
            feature="chat",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_forced_block_for_testing(self):
        """Vérifie le blocage forcé pour les tests."""
        adapter = InMemoryAbuseAdapter()

        # Configure a forced block
        adapter.configure_block(
            "app-1",
            AbuseCheckResult(
                blocked=True,
                abuse_type=AbuseType.SUSPICIOUS_PATTERN,
                reason="Test block",
            ),
        )

        result = await adapter.check_request(
            app_id="app-1",
            feature="chat",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result.blocked is True
        assert result.abuse_type == AbuseType.SUSPICIOUS_PATTERN
        assert result.reason == "Test block"

    @pytest.mark.asyncio
    async def test_clear_forced_blocks(self):
        """Vérifie l'effacement des blocages forcés."""
        adapter = InMemoryAbuseAdapter()

        adapter.configure_block(
            "app-1", AbuseCheckResult(blocked=True, abuse_type=AbuseType.LOOP_DETECTED)
        )

        adapter.clear_forced_blocks()

        result = await adapter.check_request(
            app_id="app-1",
            feature="chat",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result.blocked is False


# =============================================================================
# Tests Loop Detection
# =============================================================================


class TestLoopDetection:
    """Tests pour la détection de boucles."""

    @pytest.mark.asyncio
    async def test_duplicate_request_blocked(self):
        """Vérifie qu'une requête identique immédiate est bloquée."""
        adapter = InMemoryAbuseAdapter(dedup_window_seconds=5)

        messages = [{"role": "user", "content": "What is 2+2?"}]

        # First request
        result1 = await adapter.check_request("app-1", "chat", "gpt-4", messages)
        assert result1.blocked is False

        # Immediate duplicate
        result2 = await adapter.check_request("app-1", "chat", "gpt-4", messages)
        assert result2.blocked is True
        assert result2.abuse_type == AbuseType.DUPLICATE_REQUEST

    @pytest.mark.asyncio
    async def test_loop_detected_after_max_identical(self):
        """Vérifie la détection de boucle après trop de requêtes identiques."""
        adapter = InMemoryAbuseAdapter(
            max_identical_requests=3,
            identical_request_window_seconds=60,
            dedup_window_seconds=0,  # Disable dedup for this test
        )

        messages = [{"role": "user", "content": "Loop test"}]

        # Make max_identical_requests
        for i in range(3):
            result = await adapter.check_request("app-1", "chat", "gpt-4", messages)
            assert result.blocked is False

        # Next one should be blocked
        result = await adapter.check_request("app-1", "chat", "gpt-4", messages)
        assert result.blocked is True
        assert result.abuse_type == AbuseType.LOOP_DETECTED

    @pytest.mark.asyncio
    async def test_different_messages_not_detected_as_loop(self):
        """Vérifie que des messages différents ne sont pas détectés comme boucle."""
        adapter = InMemoryAbuseAdapter(max_identical_requests=2)

        for i in range(5):
            messages = [{"role": "user", "content": f"Message {i}"}]
            result = await adapter.check_request("app-1", "chat", "gpt-4", messages)
            assert result.blocked is False


# =============================================================================
# Tests Self-Reference Detection
# =============================================================================


class TestSelfReferenceDetection:
    """Tests pour la détection de self-référence."""

    @pytest.mark.asyncio
    async def test_self_reference_pattern_blocked(self):
        """Vérifie que les patterns de self-référence sont bloqués."""
        adapter = InMemoryAbuseAdapter()

        messages = [{"role": "user", "content": "Please call yourself again"}]
        result = await adapter.check_request("app-1", "chat", "gpt-4", messages)

        assert result.blocked is True
        assert result.abuse_type == AbuseType.SELF_REFERENCE
        assert "call yourself" in result.details.get("pattern", "")

    @pytest.mark.asyncio
    async def test_infinite_loop_pattern_blocked(self):
        """Vérifie que le pattern 'infinite loop' est bloqué."""
        adapter = InMemoryAbuseAdapter()

        messages = [{"role": "user", "content": "Create an infinite loop"}]
        result = await adapter.check_request("app-1", "chat", "gpt-4", messages)

        assert result.blocked is True
        assert result.abuse_type == AbuseType.SELF_REFERENCE

    @pytest.mark.asyncio
    async def test_normal_content_not_blocked(self):
        """Vérifie que le contenu normal n'est pas bloqué."""
        adapter = InMemoryAbuseAdapter()

        messages = [
            {
                "role": "user",
                "content": "Write a Python function to calculate factorial",
            }
        ]
        result = await adapter.check_request("app-1", "chat", "gpt-4", messages)

        assert result.blocked is False


# =============================================================================
# Tests Rate Spike Detection
# =============================================================================


class TestRateSpikeDetection:
    """Tests pour la détection de rate spike."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Vérifie que le dépassement de rate limit est détecté."""
        adapter = InMemoryAbuseAdapter(
            max_requests_per_minute=5,
            dedup_window_seconds=0,  # Disable dedup
        )

        # Make max requests
        for i in range(5):
            messages = [{"role": "user", "content": f"Request {i}"}]
            result = await adapter.check_request("app-1", "chat", "gpt-4", messages)
            assert result.blocked is False

        # Next one should be rate limited
        messages = [{"role": "user", "content": "Request 6"}]
        result = await adapter.check_request("app-1", "chat", "gpt-4", messages)

        assert result.blocked is True
        assert result.abuse_type == AbuseType.RATE_SPIKE


# =============================================================================
# Tests Error Recording
# =============================================================================


class TestErrorRecording:
    """Tests pour l'enregistrement des erreurs."""

    @pytest.mark.asyncio
    async def test_error_recording(self):
        """Vérifie l'enregistrement des erreurs."""
        adapter = InMemoryAbuseAdapter(max_errors_per_minute=3)

        for i in range(3):
            result = await adapter.record_error("app-1")
            assert result.blocked is False

        # Next error should trigger retry storm
        result = await adapter.record_error("app-1")
        assert result.blocked is True
        assert result.abuse_type == AbuseType.RETRY_STORM

    @pytest.mark.asyncio
    async def test_error_count_tracking(self):
        """Vérifie le comptage des erreurs."""
        adapter = InMemoryAbuseAdapter()

        await adapter.record_error("app-1")
        await adapter.record_error("app-1")

        assert adapter.get_error_count("app-1") == 2


# =============================================================================
# Tests Cost Recording
# =============================================================================


class TestCostRecording:
    """Tests pour l'enregistrement des coûts."""

    @pytest.mark.asyncio
    async def test_cost_spike_detection(self):
        """Vérifie la détection de spike de coût."""
        adapter = InMemoryAbuseAdapter(cost_spike_multiplier=5.0)

        # Record some normal costs
        for i in range(10):
            result = await adapter.record_cost("app-1", 0.01)
            assert result.abuse_type != AbuseType.COST_SPIKE

        # Record a spike (50x the average)
        result = await adapter.record_cost("app-1", 0.50)

        assert result.abuse_type == AbuseType.COST_SPIKE
        assert result.blocked is False  # Cost spike is a warning, not blocking

    @pytest.mark.asyncio
    async def test_normal_cost_no_spike(self):
        """Vérifie qu'un coût normal n'est pas détecté comme spike."""
        adapter = InMemoryAbuseAdapter()

        for i in range(15):
            result = await adapter.record_cost("app-1", 0.01)

        assert result.abuse_type is None


# =============================================================================
# Tests Data Clearing
# =============================================================================


class TestDataClearing:
    """Tests pour l'effacement des données."""

    @pytest.mark.asyncio
    async def test_clear_app_data(self):
        """Vérifie l'effacement des données d'une application."""
        adapter = InMemoryAbuseAdapter()

        # Generate some data
        await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "Hi"}]
        )
        await adapter.record_error("app-1")
        await adapter.record_cost("app-1", 0.01)

        assert adapter.get_request_count("app-1") == 1
        assert adapter.get_error_count("app-1") == 1

        # Clear
        await adapter.clear_app_data("app-1")

        assert adapter.get_request_count("app-1") == 0
        assert adapter.get_error_count("app-1") == 0

    def test_clear_all(self):
        """Vérifie l'effacement de toutes les données."""
        adapter = InMemoryAbuseAdapter()

        # Use internal methods to add data
        adapter._requests["app-1"] = [time.time()]
        adapter._requests["app-2"] = [time.time()]
        adapter._errors["app-1"] = [time.time()]

        adapter.clear_all()

        assert len(adapter._requests) == 0
        assert len(adapter._errors) == 0


# =============================================================================
# Tests Block Management
# =============================================================================


class TestBlockManagement:
    """Tests pour la gestion des blocages."""

    @pytest.mark.asyncio
    async def test_cooldown_blocks_subsequent_requests(self):
        """Vérifie que le cooldown bloque les requêtes suivantes."""
        adapter = InMemoryAbuseAdapter(
            max_requests_per_minute=2,
            dedup_window_seconds=0,
        )

        # Trigger rate limit
        await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "1"}]
        )
        await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "2"}]
        )
        result = await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "3"}]
        )

        assert result.blocked is True
        assert adapter.is_blocked("app-1") is True

    def test_is_blocked_helper(self):
        """Vérifie le helper is_blocked."""
        adapter = InMemoryAbuseAdapter()

        assert adapter.is_blocked("app-1") is False

        adapter.configure_block("app-1", AbuseCheckResult(blocked=True))

        assert adapter.is_blocked("app-1") is True


# =============================================================================
# Tests Isolation Between Apps
# =============================================================================


class TestAppIsolation:
    """Tests pour l'isolation entre applications."""

    @pytest.mark.asyncio
    async def test_different_apps_isolated(self):
        """Vérifie que les données sont isolées entre applications."""
        adapter = InMemoryAbuseAdapter(
            max_requests_per_minute=2, dedup_window_seconds=0
        )

        # app-1 reaches limit
        await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "1"}]
        )
        await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "2"}]
        )
        result1 = await adapter.check_request(
            "app-1", "chat", "gpt-4", [{"role": "user", "content": "3"}]
        )

        assert result1.blocked is True

        # app-2 should still work
        result2 = await adapter.check_request(
            "app-2", "chat", "gpt-4", [{"role": "user", "content": "Hi"}]
        )

        assert result2.blocked is False
