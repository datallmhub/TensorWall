package com.tensorwall.sdk;

import com.tensorwall.sdk.client.TensorWallClient;
import com.tensorwall.sdk.model.*;

import org.junit.jupiter.api.*;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * End-to-end tests against a local Ollama instance.
 *
 * Prerequisites:
 * - Ollama running on localhost:11434
 * - phi-2 model loaded
 *
 * Run with:
 *   mvn test -Dtest=OllamaE2ETest
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class OllamaE2ETest {

    private static final String OLLAMA_URL = "http://localhost:11434";
    private static final String MODEL = "phi-2";

    private TensorWallClient client;
    private boolean ollamaAvailable = false;

    @BeforeAll
    void setUp() {
        client = TensorWallClient.builder()
                .baseUrl(OLLAMA_URL)
                .build();

        // Check if Ollama is available
        try {
            ChatCompletionResponse response = client.chat(
                    List.of(ChatMessage.user("test")),
                    MODEL
            );
            ollamaAvailable = response != null && response.getContent() != null;
            if (ollamaAvailable) {
                System.out.println("✓ Ollama available at " + OLLAMA_URL + " with model " + MODEL);
            }
        } catch (Exception e) {
            System.out.println("⚠ Ollama not available at " + OLLAMA_URL + " - skipping tests");
            System.out.println("  Error: " + e.getMessage());
            System.out.println("  Start Ollama and run: ollama pull phi-2");
        }
    }

    @AfterAll
    void tearDown() {
        if (client != null) {
            client.close();
        }
    }

    private void skipIfOllamaUnavailable() {
        Assumptions.assumeTrue(ollamaAvailable, "Ollama not available");
    }

    @Test
    @Order(1)
    @DisplayName("Simple chat with Ollama")
    void testSimpleChat() {
        skipIfOllamaUnavailable();

        ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("What is 2 + 2? Answer with just the number.")),
                MODEL
        );

        assertNotNull(response);
        assertNotNull(response.getId());
        assertNotNull(response.getContent());
        assertNotNull(response.getChoices());
        assertFalse(response.getChoices().isEmpty());

        System.out.println("✓ Simple chat:");
        System.out.println("  Model: " + response.getModel());
        System.out.println("  Response: " + response.getContent().substring(0, Math.min(100, response.getContent().length())));
        if (response.getUsage() != null) {
            System.out.println("  Tokens: " + response.getUsage().getTotalTokens());
        }
    }

    @Test
    @Order(2)
    @DisplayName("Chat with system message")
    void testChatWithSystem() {
        skipIfOllamaUnavailable();

        ChatCompletionResponse response = client.chat(
                List.of(
                        ChatMessage.system("You are a helpful assistant. Always respond in exactly one word."),
                        ChatMessage.user("What color is the sky?")
                ),
                MODEL,
                0.1,
                20
        );

        assertNotNull(response);
        assertNotNull(response.getContent());

        System.out.println("✓ Chat with system message:");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(3)
    @DisplayName("Chat with temperature control")
    void testTemperature() {
        skipIfOllamaUnavailable();

        // Low temperature = more deterministic
        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model(MODEL)
                .messages(List.of(ChatMessage.user("Complete: The capital of France is")))
                .temperature(0.0)
                .maxTokens(10)
                .build();

        ChatCompletionResponse response = client.chat(request);

        assertNotNull(response);
        assertNotNull(response.getContent());

        System.out.println("✓ Temperature test (0.0):");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(4)
    @DisplayName("Multi-turn conversation")
    void testConversation() {
        skipIfOllamaUnavailable();

        ChatCompletionResponse response = client.chat(
                List.of(
                        ChatMessage.user("My favorite color is blue."),
                        ChatMessage.assistant("That's a nice color! Blue is often associated with calm and peace."),
                        ChatMessage.user("What is my favorite color?")
                ),
                MODEL
        );

        assertNotNull(response);
        String content = response.getContent().toLowerCase();

        System.out.println("✓ Conversation memory:");
        System.out.println("  Response: " + response.getContent());

        // Check if the model remembers (may not always work with small models)
        if (content.contains("blue")) {
            System.out.println("  ✓ Model remembered the color!");
        } else {
            System.out.println("  ⚠ Model may not have remembered (common with small models)");
        }
    }

    @Test
    @Order(5)
    @DisplayName("Max tokens limit")
    void testMaxTokens() {
        skipIfOllamaUnavailable();

        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model(MODEL)
                .messages(List.of(ChatMessage.user("Write a very long story about a dragon.")))
                .maxTokens(20)
                .build();

        ChatCompletionResponse response = client.chat(request);

        assertNotNull(response);
        assertNotNull(response.getContent());

        System.out.println("✓ Max tokens (20):");
        System.out.println("  Response length: " + response.getContent().length() + " chars");
        System.out.println("  Response: " + response.getContent());

        if (response.getUsage() != null) {
            System.out.println("  Completion tokens: " + response.getUsage().getCompletionTokens());
            assertTrue(response.getUsage().getCompletionTokens() <= 25, "Should respect max_tokens limit");
        }
    }

    @Test
    @Order(6)
    @DisplayName("Response time measurement")
    void testResponseTime() {
        skipIfOllamaUnavailable();

        long start = System.currentTimeMillis();

        ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("Say OK")),
                MODEL,
                0.0,
                5
        );

        long duration = System.currentTimeMillis() - start;

        assertNotNull(response);

        System.out.println("✓ Response time:");
        System.out.println("  Total: " + duration + "ms");
        System.out.println("  Response: " + response.getContent());
    }

    @Test
    @Order(99)
    @DisplayName("Summary")
    void testSummary() {
        skipIfOllamaUnavailable();

        System.out.println("\n" + "=".repeat(50));
        System.out.println("  Ollama E2E Tests Complete");
        System.out.println("=".repeat(50));
        System.out.println("  Endpoint: " + OLLAMA_URL);
        System.out.println("  Model: " + MODEL);
        System.out.println("=".repeat(50));
    }
}
