"""Tests unitaires pour les adapters LLM.

Ces tests vérifient que les adapters LLM (OpenAI, Anthropic, Mock)
implémentent correctement l'interface LLMProviderPort.
"""

import pytest
import json

from backend.adapters.llm import OpenAIAdapter, AnthropicAdapter, MockAdapter
from backend.domain.models import ChatRequest, ChatResponse, ChatMessage
from backend.ports.llm_provider import LLMProviderPort


class TestOpenAIAdapter:
    """Tests pour l'adapter OpenAI."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = OpenAIAdapter()
        assert isinstance(adapter, LLMProviderPort)

    def test_name(self):
        """Vérifie le nom du provider."""
        adapter = OpenAIAdapter()
        assert adapter.name == "openai"

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("gpt-4", True),
            ("gpt-4o", True),
            ("gpt-3.5-turbo", True),
            ("o1-preview", True),
            ("o3-mini", True),
            ("chatgpt-4o-latest", True),
            ("claude-3-opus", False),
            ("mock-gpt-4", False),
            ("llama-2", False),
        ],
    )
    def test_supports_model(self, model: str, expected: bool):
        """Vérifie la détection des modèles supportés."""
        adapter = OpenAIAdapter()
        assert adapter.supports_model(model) == expected

    def test_custom_base_url(self):
        """Vérifie la configuration de l'URL de base."""
        adapter = OpenAIAdapter(base_url="https://custom.openai.com/v1")
        assert adapter._base_url == "https://custom.openai.com/v1"

    def test_custom_timeout(self):
        """Vérifie la configuration du timeout."""
        adapter = OpenAIAdapter(timeout=120.0)
        assert adapter._timeout == 120.0

    @pytest.mark.asyncio
    async def test_chat_builds_correct_payload(self):
        """Vérifie que le payload est correctement construit."""
        adapter = OpenAIAdapter()
        request = ChatRequest(
            model="gpt-4",
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello"),
            ],
            max_tokens=100,
            temperature=0.7,
        )

        payload = adapter._build_payload(request, stream=False)

        assert payload["model"] == "gpt-4"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are helpful."
        assert payload["max_tokens"] == 100
        assert payload["temperature"] == 0.7
        assert payload["stream"] is False

    def test_parse_response(self):
        """Vérifie le parsing de la réponse."""
        adapter = OpenAIAdapter()
        data = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"content": "Hello back!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        }

        response = adapter._parse_response(data)

        assert isinstance(response, ChatResponse)
        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-4"
        assert response.content == "Hello back!"
        assert response.input_tokens == 10
        assert response.output_tokens == 5
        assert response.finish_reason == "stop"


class TestAnthropicAdapter:
    """Tests pour l'adapter Anthropic."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = AnthropicAdapter()
        assert isinstance(adapter, LLMProviderPort)

    def test_name(self):
        """Vérifie le nom du provider."""
        adapter = AnthropicAdapter()
        assert adapter.name == "anthropic"

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("claude-3-opus", True),
            ("claude-3-sonnet", True),
            ("claude-3-5-sonnet", True),
            ("claude-2", True),
            ("gpt-4", False),
            ("mock-claude", False),
        ],
    )
    def test_supports_model(self, model: str, expected: bool):
        """Vérifie la détection des modèles supportés."""
        adapter = AnthropicAdapter()
        assert adapter.supports_model(model) == expected

    def test_convert_messages_extracts_system(self):
        """Vérifie l'extraction du message système."""
        adapter = AnthropicAdapter()
        messages = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi!"),
        ]

        system, anthropic_messages = adapter._convert_messages(messages)

        assert system == "You are helpful."
        assert len(anthropic_messages) == 2
        assert anthropic_messages[0]["role"] == "user"
        assert anthropic_messages[1]["role"] == "assistant"

    def test_convert_messages_no_system(self):
        """Vérifie la conversion sans message système."""
        adapter = AnthropicAdapter()
        messages = [
            ChatMessage(role="user", content="Hello"),
        ]

        system, anthropic_messages = adapter._convert_messages(messages)

        assert system is None
        assert len(anthropic_messages) == 1

    def test_parse_response(self):
        """Vérifie le parsing de la réponse Anthropic."""
        adapter = AnthropicAdapter()
        data = {
            "id": "msg_123",
            "model": "claude-3-opus",
            "content": [{"type": "text", "text": "Hello!"}],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
            },
            "stop_reason": "end_turn",
        }

        response = adapter._parse_response(data)

        assert isinstance(response, ChatResponse)
        assert response.id == "msg_123"
        assert response.content == "Hello!"
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    def test_convert_stream_event_text_delta(self):
        """Vérifie la conversion des événements de streaming."""
        adapter = AnthropicAdapter()
        event = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello"},
        }

        result = adapter._convert_stream_event(event)

        assert result["choices"][0]["delta"]["content"] == "Hello"

    def test_convert_stream_event_message_stop(self):
        """Vérifie la détection de fin de message."""
        adapter = AnthropicAdapter()
        event = {"type": "message_stop"}

        result = adapter._convert_stream_event(event)

        assert result is None


class TestMockAdapter:
    """Tests pour l'adapter Mock."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = MockAdapter()
        assert isinstance(adapter, LLMProviderPort)

    def test_name(self):
        """Vérifie le nom du provider."""
        adapter = MockAdapter()
        assert adapter.name == "mock"

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("mock-gpt-4", True),
            ("mock-claude", True),
            ("test-model", True),
            ("gpt-4", False),
            ("claude-3-opus", False),
        ],
    )
    def test_supports_model(self, model: str, expected: bool):
        """Vérifie la détection des modèles supportés."""
        adapter = MockAdapter()
        assert adapter.supports_model(model) == expected

    @pytest.mark.asyncio
    async def test_chat_returns_mock_response(self):
        """Vérifie que chat retourne une réponse mock."""
        adapter = MockAdapter(latency=0)  # Pas de latence pour les tests
        request = ChatRequest(
            model="mock-gpt-4",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        response = await adapter.chat(request, "fake-api-key")

        assert isinstance(response, ChatResponse)
        assert response.model == "mock-gpt-4"
        assert "Hello" in response.content
        assert response.finish_reason == "stop"
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_chat_with_fixed_response(self):
        """Vérifie la réponse fixe."""
        adapter = MockAdapter(latency=0, fixed_response="Fixed response!")
        request = ChatRequest(
            model="mock-gpt-4",
            messages=[ChatMessage(role="user", content="Hello")],
        )

        response = await adapter.chat(request, "fake-api-key")

        assert response.content == "Fixed response!"

    @pytest.mark.asyncio
    async def test_chat_stream_yields_chunks(self):
        """Vérifie le streaming."""
        adapter = MockAdapter(latency=0, stream_delay=0, fixed_response="Hello world")
        request = ChatRequest(
            model="mock-gpt-4",
            messages=[ChatMessage(role="user", content="Test")],
        )

        chunks = []
        async for chunk in adapter.chat_stream(request, "fake-api-key"):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Vérifier que le dernier chunk contient finish_reason
        last_chunk = json.loads(chunks[-1])
        assert last_chunk["choices"][0].get("finish_reason") == "stop"

    def test_estimate_tokens(self):
        """Vérifie l'estimation des tokens."""
        adapter = MockAdapter()
        messages = [
            ChatMessage(role="user", content="Hello world"),  # 2 mots
        ]

        tokens = adapter._estimate_tokens(messages)

        # ~1.3 tokens par mot
        assert tokens == int(2 * 1.3)
