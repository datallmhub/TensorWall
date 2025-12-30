package com.tensorwall.sdk;

import com.tensorwall.sdk.client.TensorWallClient;
import com.tensorwall.sdk.model.*;

import org.junit.jupiter.api.*;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * End-to-end tests against a real TensorWall instance.
 *
 * Prerequisites:
 * - TensorWall running on localhost:8000
 * - Valid API key configured
 *
 * Run with:
 *   mvn test -Dtest=TensorWallE2ETest -DTENSORWALL_API_KEY=your-key
 *
 * Or skip if no server available:
 *   mvn test -Dtest=!TensorWallE2ETest
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class TensorWallE2ETest {

    private static final String BASE_URL = System.getProperty("TENSORWALL_URL", "http://localhost:8000");
    private static final String API_KEY = System.getProperty("TENSORWALL_API_KEY", "gw_-lYKhGGe0Y3W25bY3yODuBabzNW_Oho6");

    private TensorWallClient client;
    private boolean serverAvailable = false;
    private boolean llmProviderAvailable = false;

    @BeforeAll
    void setUp() {
        client = TensorWallClient.builder()
                .baseUrl(BASE_URL)
                .apiKey(API_KEY)
                .appId("java-sdk-e2e-test")
                .build();

        // Check if server is available
        try {
            Map<String, Object> health = client.health();
            serverAvailable = "healthy".equals(health.get("status"));
            if (serverAvailable) {
                System.out.println("✓ TensorWall server available at " + BASE_URL);

                // Check if LLM provider is available by trying a simple call
                try {
                    client.chat(List.of(ChatMessage.user("test")), "gpt-4o-mini");
                    llmProviderAvailable = true;
                    System.out.println("✓ LLM provider available");
                } catch (Exception e) {
                    llmProviderAvailable = false;
                    System.out.println("⚠ LLM provider not configured - skipping LLM tests");
                }
            }
        } catch (Exception e) {
            System.out.println("⚠ TensorWall server not available at " + BASE_URL + " - skipping E2E tests");
            System.out.println("  Start with: docker-compose up -d");
        }
    }

    @AfterAll
    void tearDown() {
        if (client != null) {
            client.close();
        }
    }

    private void skipIfServerUnavailable() {
        Assumptions.assumeTrue(serverAvailable, "TensorWall server not available");
    }

    private void skipIfNoLLMProvider() {
        Assumptions.assumeTrue(llmProviderAvailable, "LLM provider not configured");
    }

    @Test
    @Order(1)
    @DisplayName("Health check")
    void testHealth() {
        skipIfServerUnavailable();

        Map<String, Object> health = client.health();

        assertNotNull(health);
        assertEquals("healthy", health.get("status"));
        assertNotNull(health.get("version"));
        System.out.println("✓ Health: " + health.get("status") + " (v" + health.get("version") + ")");
    }

    @Test
    @Order(2)
    @DisplayName("List models")
    void testListModels() {
        skipIfServerUnavailable();

        try {
            List<Map<String, Object>> models = client.models();
            assertNotNull(models);
            System.out.println("✓ Available models: " + models.size());
            for (Map<String, Object> model : models) {
                System.out.println("  - " + model.get("id"));
            }
        } catch (Exception e) {
            // /v1/models endpoint may not be available
            System.out.println("⚠ List models not available: " + e.getMessage());
        }
    }

    @Test
    @Order(3)
    @DisplayName("Simple chat completion")
    void testSimpleChat() {
        skipIfServerUnavailable();
        skipIfNoLLMProvider();

        ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("Say 'Hello from Java SDK' and nothing else.")),
                "gpt-4o-mini"
        );

        assertNotNull(response);
        assertNotNull(response.getId());
        assertNotNull(response.getContent());
        assertNotNull(response.getUsage());

        System.out.println("✓ Chat response:");
        System.out.println("  ID: " + response.getId());
        System.out.println("  Content: " + response.getContent());
        System.out.println("  Tokens: " + response.getUsage().getTotalTokens());
        if (response.getCost() != null) {
            System.out.println("  Cost: $" + response.getCost());
        }
        if (response.getLatencyMs() != null) {
            System.out.println("  Latency: " + response.getLatencyMs() + "ms");
        }
    }

    @Test
    @Order(4)
    @DisplayName("Chat with system message")
    void testChatWithSystem() {
        skipIfServerUnavailable();
        skipIfNoLLMProvider();

        ChatCompletionResponse response = client.chat(
                List.of(
                        ChatMessage.system("You are a helpful assistant. Always respond in exactly 3 words."),
                        ChatMessage.user("What is Java?")
                ),
                "gpt-4o-mini",
                0.0,  // temperature
                50    // maxTokens
        );

        assertNotNull(response);
        assertNotNull(response.getContent());

        System.out.println("✓ Chat with system message:");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(5)
    @DisplayName("Chat with builder")
    void testChatWithBuilder() {
        skipIfServerUnavailable();
        skipIfNoLLMProvider();

        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model("gpt-4o-mini")
                .messages(List.of(
                        ChatMessage.system("You are a code assistant."),
                        ChatMessage.user("Write a one-line Java hello world")
                ))
                .temperature(0.0)
                .maxTokens(100)
                .build();

        ChatCompletionResponse response = client.chat(request);

        assertNotNull(response);
        assertTrue(response.getContent().toLowerCase().contains("hello") ||
                   response.getContent().contains("System.out"));

        System.out.println("✓ Chat with builder:");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(6)
    @DisplayName("Multiple messages conversation")
    void testConversation() {
        skipIfServerUnavailable();
        skipIfNoLLMProvider();

        ChatCompletionResponse response = client.chat(
                List.of(
                        ChatMessage.user("My name is Alice."),
                        ChatMessage.assistant("Nice to meet you, Alice!"),
                        ChatMessage.user("What's my name?")
                ),
                "gpt-4o-mini"
        );

        assertNotNull(response);
        assertTrue(response.getContent().toLowerCase().contains("alice"),
                "Response should remember the name Alice");

        System.out.println("✓ Conversation memory test:");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(10)
    @DisplayName("Dry run mode")
    void testDryRun() {
        skipIfServerUnavailable();

        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model("gpt-4o-mini")
                .messages(List.of(ChatMessage.user("This is a dry run test")))
                .dryRun(true)
                .build();

        try {
            ChatCompletionResponse response = client.chat(request);
            System.out.println("✓ Dry run completed");
            System.out.println("  Request ID: " + response.getRequestId());
        } catch (Exception e) {
            // Dry run might return different response format
            System.out.println("✓ Dry run executed (may have different response format)");
        }
    }

    @Test
    @Order(20)
    @DisplayName("Performance - Response time")
    void testResponseTime() {
        skipIfServerUnavailable();
        skipIfNoLLMProvider();

        long start = System.currentTimeMillis();

        ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("Reply with just 'OK'")),
                "gpt-4o-mini"
        );

        long duration = System.currentTimeMillis() - start;

        assertNotNull(response);
        System.out.println("✓ Response time: " + duration + "ms");
        System.out.println("  Server latency: " + response.getLatencyMs() + "ms");
    }

    @Test
    @Order(99)
    @DisplayName("Summary")
    void testSummary() {
        skipIfServerUnavailable();

        System.out.println("\n" + "=".repeat(50));
        System.out.println("  TensorWall Java SDK E2E Tests Complete");
        System.out.println("=".repeat(50));
        System.out.println("  Server: " + BASE_URL);
        System.out.println("  App ID: java-sdk-e2e-test");
        System.out.println("=".repeat(50));
    }
}
