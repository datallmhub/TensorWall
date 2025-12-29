"""Tests unitaires pour les adapters d'audit.

Ces tests vérifient que les adapters d'audit (PostgreSQL, InMemory)
implémentent correctement l'interface AuditLogPort.
"""

import pytest
from datetime import datetime, timedelta

from backend.adapters.audit import InMemoryAuditAdapter
from backend.ports.audit_log import AuditLogPort, AuditEntry


class TestInMemoryAuditAdapter:
    """Tests pour l'adapter InMemory (utilisé pour les tests)."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = InMemoryAuditAdapter()
        assert isinstance(adapter, AuditLogPort)

    @pytest.mark.asyncio
    async def test_log_entry(self):
        """Vérifie l'enregistrement d'une entrée."""
        adapter = InMemoryAuditAdapter()

        entry = AuditEntry(
            event_type="request",
            request_id="req-123",
            app_id="test-app",
            model="gpt-4",
            outcome="allowed",
        )

        await adapter.log(entry)

        assert len(adapter.entries) == 1
        assert adapter.entries[0].request_id == "req-123"

    @pytest.mark.asyncio
    async def test_log_request(self):
        """Vérifie log_request crée une entrée correcte."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_request(
            request_id="req-456",
            app_id="my-app",
            model="gpt-3.5-turbo",
            outcome="allowed",
            details={"feature": "chat"},
        )

        assert len(adapter.entries) == 1
        entry = adapter.entries[0]
        assert entry.event_type == "request"
        assert entry.request_id == "req-456"
        assert entry.app_id == "my-app"
        assert entry.model == "gpt-3.5-turbo"
        assert entry.outcome == "allowed"
        assert entry.details["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_log_policy_decision(self):
        """Vérifie log_policy_decision crée une entrée correcte."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_policy_decision(
            request_id="req-789",
            app_id="my-app",
            policy_id="policy-1",
            action="deny",
            reason="Model not allowed",
        )

        assert len(adapter.entries) == 1
        entry = adapter.entries[0]
        assert entry.event_type == "policy_decision"
        assert entry.request_id == "req-789"
        assert entry.action == "deny"
        assert entry.details["policy_id"] == "policy-1"
        assert entry.details["reason"] == "Model not allowed"

    @pytest.mark.asyncio
    async def test_get_entries_no_filter(self):
        """Vérifie get_entries sans filtre."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_request("req-1", "app-1", "gpt-4", "allowed")
        await adapter.log_request("req-2", "app-2", "gpt-3.5", "denied")

        entries = await adapter.get_entries()

        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_app_id(self):
        """Vérifie le filtrage par app_id."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_request("req-1", "app-1", "gpt-4", "allowed")
        await adapter.log_request("req-2", "app-2", "gpt-3.5", "denied")
        await adapter.log_request("req-3", "app-1", "gpt-4", "allowed")

        entries = await adapter.get_entries(app_id="app-1")

        assert len(entries) == 2
        assert all(e.app_id == "app-1" for e in entries)

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_org_id(self):
        """Vérifie le filtrage par org_id."""
        adapter = InMemoryAuditAdapter()

        entry1 = AuditEntry(
            event_type="request",
            request_id="req-1",
            app_id="app-1",
            org_id="org-A",
        )
        entry2 = AuditEntry(
            event_type="request",
            request_id="req-2",
            app_id="app-1",
            org_id="org-B",
        )

        await adapter.log(entry1)
        await adapter.log(entry2)

        entries = await adapter.get_entries(org_id="org-A")

        assert len(entries) == 1
        assert entries[0].org_id == "org-A"

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_event_type(self):
        """Vérifie le filtrage par event_type."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_request("req-1", "app-1", "gpt-4", "allowed")
        await adapter.log_policy_decision("req-2", "app-1", "pol-1", "deny", "Test")

        entries = await adapter.get_entries(event_type="policy_decision")

        assert len(entries) == 1
        assert entries[0].event_type == "policy_decision"

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_time_range(self):
        """Vérifie le filtrage par plage de temps."""
        adapter = InMemoryAuditAdapter()

        now = datetime.utcnow()
        old_entry = AuditEntry(
            event_type="request",
            request_id="req-old",
            app_id="app-1",
            timestamp=now - timedelta(hours=2),
        )
        new_entry = AuditEntry(
            event_type="request",
            request_id="req-new",
            app_id="app-1",
            timestamp=now,
        )

        await adapter.log(old_entry)
        await adapter.log(new_entry)

        entries = await adapter.get_entries(
            start_time=now - timedelta(hours=1),
        )

        assert len(entries) == 1
        assert entries[0].request_id == "req-new"

    @pytest.mark.asyncio
    async def test_get_entries_limit(self):
        """Vérifie la limite de résultats."""
        adapter = InMemoryAuditAdapter()

        for i in range(10):
            await adapter.log_request(f"req-{i}", "app-1", "gpt-4", "allowed")

        entries = await adapter.get_entries(limit=5)

        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_get_entries_sorted_by_timestamp_desc(self):
        """Vérifie le tri par timestamp décroissant."""
        adapter = InMemoryAuditAdapter()

        now = datetime.utcnow()
        for i in range(3):
            entry = AuditEntry(
                event_type="request",
                request_id=f"req-{i}",
                app_id="app-1",
                timestamp=now + timedelta(minutes=i),
            )
            await adapter.log(entry)

        entries = await adapter.get_entries()

        # Plus récent en premier
        assert entries[0].request_id == "req-2"
        assert entries[1].request_id == "req-1"
        assert entries[2].request_id == "req-0"

    @pytest.mark.asyncio
    async def test_clear(self):
        """Vérifie le vidage des entrées."""
        adapter = InMemoryAuditAdapter()

        await adapter.log_request("req-1", "app-1", "gpt-4", "allowed")
        await adapter.log_request("req-2", "app-1", "gpt-4", "allowed")

        assert len(adapter.entries) == 2

        adapter.clear()

        assert len(adapter.entries) == 0

    @pytest.mark.asyncio
    async def test_entry_with_all_fields(self):
        """Vérifie qu'une entrée complète est bien stockée."""
        adapter = InMemoryAuditAdapter()

        entry = AuditEntry(
            event_type="llm_request",
            request_id="req-full",
            app_id="test-app",
            org_id="org-123",
            user_id="user-456",
            model="gpt-4",
            action="allow",
            outcome="allowed",
            details={"feature": "chat", "environment": "production"},
            duration_ms=150,
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0045,
        )

        await adapter.log(entry)

        result = adapter.entries[0]
        assert result.event_type == "llm_request"
        assert result.org_id == "org-123"
        assert result.user_id == "user-456"
        assert result.duration_ms == 150
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.cost_usd == 0.0045

    @pytest.mark.asyncio
    async def test_multiple_filters_combined(self):
        """Vérifie que plusieurs filtres fonctionnent ensemble."""
        adapter = InMemoryAuditAdapter()

        now = datetime.utcnow()

        # Entrée qui match tous les critères
        entry1 = AuditEntry(
            event_type="request",
            request_id="match",
            app_id="target-app",
            org_id="target-org",
            timestamp=now,
        )

        # Entrée avec mauvais app_id
        entry2 = AuditEntry(
            event_type="request",
            request_id="wrong-app",
            app_id="other-app",
            org_id="target-org",
            timestamp=now,
        )

        # Entrée avec mauvais org_id
        entry3 = AuditEntry(
            event_type="request",
            request_id="wrong-org",
            app_id="target-app",
            org_id="other-org",
            timestamp=now,
        )

        await adapter.log(entry1)
        await adapter.log(entry2)
        await adapter.log(entry3)

        entries = await adapter.get_entries(
            app_id="target-app",
            org_id="target-org",
        )

        assert len(entries) == 1
        assert entries[0].request_id == "match"
