"""LLM Gateway SDK data models."""

from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant", "function", "tool"]
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Request for chat completion."""

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    user: Optional[str] = None

    # LLM Gateway specific
    app_id: Optional[str] = None
    feature: Optional[str] = None
    dry_run: bool = False


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatChoice(BaseModel):
    """A single choice in chat completion response."""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Response from chat completion."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Optional[Usage] = None

    # LLM Gateway metadata
    request_id: Optional[str] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None


class EmbeddingRequest(BaseModel):
    """Request for embeddings."""

    model: str
    input: Union[str, List[str]]
    encoding_format: Optional[Literal["float", "base64"]] = None
    dimensions: Optional[int] = None
    user: Optional[str] = None

    # LLM Gateway specific
    app_id: Optional[str] = None
    feature: Optional[str] = None
    dry_run: bool = False


class EmbeddingData(BaseModel):
    """A single embedding result."""

    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    """Response from embeddings."""

    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Usage

    # LLM Gateway metadata
    request_id: Optional[str] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None


class StreamDelta(BaseModel):
    """Delta content for streaming."""

    role: Optional[str] = None
    content: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamChoice(BaseModel):
    """A single choice in streaming response."""

    index: int
    delta: StreamDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """A chunk in streaming chat completion."""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]
