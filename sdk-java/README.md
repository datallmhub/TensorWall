# TensorWall Java SDK

Java SDK for [TensorWall](https://github.com/datallmhub/TensorWall) - A unified API gateway for multiple LLM providers.

## Requirements

- Java 17+
- Maven or Gradle

## Installation

### Maven

```xml
<dependency>
    <groupId>com.tensorwall</groupId>
    <artifactId>tensorwall-sdk</artifactId>
    <version>0.2.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'com.tensorwall:tensorwall-sdk:0.1.0'
```

## Quick Start

```java
import com.tensorwall.sdk.client.TensorWallClient;
import com.tensorwall.sdk.model.ChatMessage;
import com.tensorwall.sdk.model.ChatCompletionResponse;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        try (TensorWallClient client = TensorWallClient.builder()
                .baseUrl("http://localhost:8000")
                .apiKey("your-api-key")
                .build()) {

            // Simple chat
            ChatCompletionResponse response = client.chat(
                List.of(ChatMessage.user("Hello!")),
                "gpt-4"
            );

            System.out.println(response.getContent());
        }
    }
}
```

## Features

### Chat Completions

```java
// Simple message
ChatCompletionResponse response = client.chat(
    List.of(ChatMessage.user("What is 2+2?")),
    "gpt-4"
);

// With temperature and max tokens
ChatCompletionResponse response = client.chat(
    List.of(
        ChatMessage.system("You are a helpful assistant."),
        ChatMessage.user("Explain quantum computing")
    ),
    "gpt-4",
    0.7,  // temperature
    500   // maxTokens
);

// Using builder for full control
ChatCompletionRequest request = ChatCompletionRequest.builder()
    .model("gpt-4")
    .messages(List.of(
        ChatMessage.system("You are a code assistant."),
        ChatMessage.user("Write a hello world in Java")
    ))
    .temperature(0.0)
    .maxTokens(1000)
    .build();

ChatCompletionResponse response = client.chat(request);
```

### Embeddings

```java
// Single text
EmbeddingResponse response = client.embeddings(
    "Hello world",
    "text-embedding-ada-002"
);
List<Double> embedding = response.getFirstEmbedding();

// Multiple texts
EmbeddingResponse response = client.embeddings(
    List.of("Hello", "World"),
    "text-embedding-ada-002"
);
```

### Health Check

```java
Map<String, Object> health = client.health();
System.out.println(health.get("status")); // "healthy"
```

### List Models

```java
List<Map<String, Object>> models = client.models();
for (Map<String, Object> model : models) {
    System.out.println(model.get("id"));
}
```

## Configuration

```java
TensorWallClient client = TensorWallClient.builder()
    .baseUrl("http://localhost:8000")  // Gateway URL
    .apiKey("your-api-key")            // API key
    .appId("my-app")                   // Application ID for tracking
    .orgId("my-org")                   // Organization ID
    .timeout(120)                      // Timeout in seconds
    .build();
```

## Error Handling

```java
import com.tensorwall.sdk.exception.*;

try {
    ChatCompletionResponse response = client.chat(messages, model);
} catch (AuthenticationException e) {
    // Invalid API key (401/403)
    System.err.println("Auth failed: " + e.getMessage());
} catch (RateLimitException e) {
    // Rate limit exceeded (429)
    System.err.println("Rate limited. Retry after: " + e.getRetryAfter());
} catch (ValidationException e) {
    // Invalid request (400/422)
    System.err.println("Validation error: " + e.getMessage());
} catch (PolicyDeniedException e) {
    // Blocked by policy
    System.err.println("Policy denied: " + e.getPolicyName());
} catch (BudgetExceededException e) {
    // Budget limit reached
    System.err.println("Budget exceeded: " + e.getLimit() + " (current: " + e.getCurrent() + ")");
} catch (ServerException e) {
    // Server error (5xx)
    System.err.println("Server error: " + e.getMessage());
} catch (TensorWallException e) {
    // Other errors
    System.err.println("Error: " + e.getMessage());
}
```

## Response Metadata

TensorWall adds metadata to responses:

```java
ChatCompletionResponse response = client.chat(messages, model);

// Standard OpenAI fields
String content = response.getContent();
ChatCompletionResponse.Usage usage = response.getUsage();
int totalTokens = usage.getTotalTokens();

// TensorWall metadata
String requestId = response.getRequestId();
Double cost = response.getCost();
Double latencyMs = response.getLatencyMs();
```

## Thread Safety

The `TensorWallClient` is thread-safe and can be shared across threads. It's recommended to create a single instance and reuse it.

```java
// Create once, use everywhere
public class App {
    private static final TensorWallClient client = TensorWallClient.builder()
        .apiKey(System.getenv("TENSORWALL_API_KEY"))
        .build();

    public static TensorWallClient getClient() {
        return client;
    }
}
```

## License

MIT
