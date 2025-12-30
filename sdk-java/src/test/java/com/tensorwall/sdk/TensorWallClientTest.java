package com.tensorwall.sdk;

import com.tensorwall.sdk.client.TensorWallClient;
import com.tensorwall.sdk.exception.*;
import com.tensorwall.sdk.model.*;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;

import org.junit.jupiter.api.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class TensorWallClientTest {

    private MockWebServer mockServer;
    private TensorWallClient client;

    @BeforeEach
    void setUp() throws IOException {
        mockServer = new MockWebServer();
        mockServer.start();

        client = TensorWallClient.builder()
                .baseUrl(mockServer.url("/").toString())
                .apiKey("test-api-key")
                .appId("test-app")
                .build();
    }

    @AfterEach
    void tearDown() throws IOException {
        client.close();
        mockServer.shutdown();
    }

    @Test
    void testChatCompletion() throws InterruptedException {
        String responseJson = """
            {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you?"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18
                },
                "request_id": "req-123",
                "cost": 0.0001,
                "latency_ms": 150.5
            }
            """;

        mockServer.enqueue(new MockResponse()
                .setBody(responseJson)
                .setHeader("Content-Type", "application/json"));

        ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("Hello!")),
                "gpt-4"
        );

        // Verify response
        assertEquals("chatcmpl-123", response.getId());
        assertEquals("gpt-4", response.getModel());
        assertEquals("Hello! How can I help you?", response.getContent());
        assertEquals(18, response.getUsage().getTotalTokens());
        assertEquals("req-123", response.getRequestId());
        assertEquals(0.0001, response.getCost());

        // Verify request
        RecordedRequest request = mockServer.takeRequest();
        assertEquals("POST", request.getMethod());
        assertEquals("/v1/chat/completions", request.getPath());
        assertEquals("test-api-key", request.getHeader("X-API-Key"));
        assertEquals("test-app", request.getHeader("X-App-ID"));
        assertTrue(request.getBody().readUtf8().contains("\"model\":\"gpt-4\""));
    }

    @Test
    void testChatWithOptions() throws InterruptedException {
        mockServer.enqueue(new MockResponse()
                .setBody("""
                    {
                        "id": "chatcmpl-123",
                        "object": "chat.completion",
                        "created": 1234567890,
                        "model": "gpt-4",
                        "choices": [{
                            "index": 0,
                            "message": {"role": "assistant", "content": "Response"},
                            "finish_reason": "stop"
                        }]
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        ChatCompletionResponse response = client.chat(
                List.of(
                        ChatMessage.system("You are helpful."),
                        ChatMessage.user("Hi")
                ),
                "gpt-4",
                0.7,
                100
        );

        assertEquals("Response", response.getContent());

        RecordedRequest request = mockServer.takeRequest();
        String body = request.getBody().readUtf8();
        assertTrue(body.contains("\"temperature\":0.7"));
        assertTrue(body.contains("\"max_tokens\":100"));
    }

    @Test
    void testEmbeddings() throws InterruptedException {
        mockServer.enqueue(new MockResponse()
                .setBody("""
                    {
                        "object": "list",
                        "data": [{
                            "object": "embedding",
                            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                            "index": 0
                        }],
                        "model": "text-embedding-ada-002",
                        "usage": {
                            "prompt_tokens": 5,
                            "total_tokens": 5
                        }
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        EmbeddingResponse response = client.embeddings("Hello world", "text-embedding-ada-002");

        assertEquals("text-embedding-ada-002", response.getModel());
        assertNotNull(response.getFirstEmbedding());
        assertEquals(5, response.getFirstEmbedding().size());
        assertEquals(0.1, response.getFirstEmbedding().get(0));

        RecordedRequest request = mockServer.takeRequest();
        assertEquals("POST", request.getMethod());
        assertEquals("/v1/embeddings", request.getPath());
    }

    @Test
    void testEmbeddingsMultipleInputs() throws InterruptedException {
        mockServer.enqueue(new MockResponse()
                .setBody("""
                    {
                        "object": "list",
                        "data": [
                            {"object": "embedding", "embedding": [0.1, 0.2], "index": 0},
                            {"object": "embedding", "embedding": [0.3, 0.4], "index": 1}
                        ],
                        "model": "text-embedding-ada-002",
                        "usage": {"prompt_tokens": 4, "total_tokens": 4}
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        EmbeddingResponse response = client.embeddings(
                List.of("Hello", "World"),
                "text-embedding-ada-002"
        );

        assertEquals(2, response.getData().size());
    }

    @Test
    void testHealth() {
        mockServer.enqueue(new MockResponse()
                .setBody("""
                    {
                        "status": "healthy",
                        "version": "0.1.0",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        Map<String, Object> health = client.health();

        assertEquals("healthy", health.get("status"));
        assertEquals("0.1.0", health.get("version"));
    }

    @Test
    void testModels() {
        mockServer.enqueue(new MockResponse()
                .setBody("""
                    {
                        "data": [
                            {"id": "gpt-4", "object": "model"},
                            {"id": "gpt-3.5-turbo", "object": "model"}
                        ]
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        List<Map<String, Object>> models = client.models();

        assertEquals(2, models.size());
        assertEquals("gpt-4", models.get(0).get("id"));
    }

    @Test
    void testAuthenticationError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(401)
                .setBody("""
                    {"detail": "Invalid API key"}
                    """)
                .setHeader("Content-Type", "application/json"));

        AuthenticationException exception = assertThrows(
                AuthenticationException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "gpt-4")
        );

        assertEquals(401, exception.getStatusCode());
        assertTrue(exception.getMessage().contains("Invalid API key"));
    }

    @Test
    void testRateLimitError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(429)
                .setBody("""
                    {"detail": "Rate limit exceeded"}
                    """)
                .setHeader("Content-Type", "application/json")
                .setHeader("Retry-After", "30"));

        RateLimitException exception = assertThrows(
                RateLimitException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "gpt-4")
        );

        assertEquals(429, exception.getStatusCode());
        assertEquals(30, exception.getRetryAfter());
    }

    @Test
    void testValidationError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(422)
                .setBody("""
                    {"detail": "Invalid model specified"}
                    """)
                .setHeader("Content-Type", "application/json"));

        ValidationException exception = assertThrows(
                ValidationException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "invalid-model")
        );

        assertEquals(422, exception.getStatusCode());
    }

    @Test
    void testServerError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(500)
                .setBody("""
                    {"detail": "Internal server error"}
                    """)
                .setHeader("Content-Type", "application/json"));

        ServerException exception = assertThrows(
                ServerException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "gpt-4")
        );

        assertEquals(500, exception.getStatusCode());
    }

    @Test
    void testPolicyDeniedError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(403)
                .setBody("""
                    {
                        "detail": "Request blocked by policy",
                        "error_code": "policy_denied",
                        "policy_name": "production-rate-limit"
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        PolicyDeniedException exception = assertThrows(
                PolicyDeniedException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "gpt-4")
        );

        assertEquals("production-rate-limit", exception.getPolicyName());
    }

    @Test
    void testBudgetExceededError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(403)
                .setBody("""
                    {
                        "detail": "Budget limit exceeded",
                        "error_code": "budget_exceeded",
                        "budget_type": "monthly",
                        "limit": 100.0,
                        "current": 105.5
                    }
                    """)
                .setHeader("Content-Type", "application/json"));

        BudgetExceededException exception = assertThrows(
                BudgetExceededException.class,
                () -> client.chat(List.of(ChatMessage.user("Hi")), "gpt-4")
        );

        assertEquals("monthly", exception.getBudgetType());
        assertEquals(100.0, exception.getLimit());
        assertEquals(105.5, exception.getCurrent());
    }

    @Test
    void testChatMessageFactoryMethods() {
        ChatMessage system = ChatMessage.system("You are helpful");
        assertEquals("system", system.getRole());
        assertEquals("You are helpful", system.getContent());

        ChatMessage user = ChatMessage.user("Hello");
        assertEquals("user", user.getRole());
        assertEquals("Hello", user.getContent());

        ChatMessage assistant = ChatMessage.assistant("Hi there");
        assertEquals("assistant", assistant.getRole());
        assertEquals("Hi there", assistant.getContent());
    }

    @Test
    void testRequestBuilder() {
        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model("gpt-4")
                .messages(List.of(ChatMessage.user("Hi")))
                .temperature(0.5)
                .maxTokens(100)
                .topP(0.9)
                .appId("my-app")
                .feature("chat")
                .dryRun(true)
                .build();

        assertEquals("gpt-4", request.getModel());
        assertEquals(0.5, request.getTemperature());
        assertEquals(100, request.getMaxTokens());
        assertEquals(0.9, request.getTopP());
        assertEquals("my-app", request.getAppId());
        assertEquals("chat", request.getFeature());
        assertTrue(request.getDryRun());
    }

    @Test
    void testEmbeddingRequestBuilder() {
        EmbeddingRequest request = EmbeddingRequest.builder()
                .model("text-embedding-ada-002")
                .input("Hello world")
                .dimensions(256)
                .appId("my-app")
                .build();

        assertEquals("text-embedding-ada-002", request.getModel());
        assertEquals("Hello world", request.getInput());
        assertEquals(256, request.getDimensions());
        assertEquals("my-app", request.getAppId());
    }
}
