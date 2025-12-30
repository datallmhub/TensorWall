package com.tensorwall.sdk.client;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tensorwall.sdk.exception.*;
import com.tensorwall.sdk.model.*;

import okhttp3.*;

import java.io.Closeable;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * TensorWall Java SDK client.
 *
 * <pre>{@code
 * try (TensorWallClient client = TensorWallClient.builder()
 *         .baseUrl("http://localhost:8000")
 *         .apiKey("your-api-key")
 *         .build()) {
 *
 *     ChatCompletionResponse response = client.chat(
 *         List.of(ChatMessage.user("Hello!")),
 *         "gpt-4"
 *     );
 *     System.out.println(response.getContent());
 * }
 * }</pre>
 */
public class TensorWallClient implements Closeable {
    private static final String DEFAULT_BASE_URL = "http://localhost:8000";
    private static final long DEFAULT_TIMEOUT_SECONDS = 60;
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final String baseUrl;
    private final String apiKey;
    private final String appId;
    private final String orgId;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;

    private TensorWallClient(Builder builder) {
        this.baseUrl = builder.baseUrl != null ? builder.baseUrl.replaceAll("/$", "") : DEFAULT_BASE_URL;
        this.apiKey = builder.apiKey;
        this.appId = builder.appId;
        this.orgId = builder.orgId;
        this.objectMapper = new ObjectMapper();

        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(builder.timeoutSeconds, TimeUnit.SECONDS)
                .readTimeout(builder.timeoutSeconds, TimeUnit.SECONDS)
                .writeTimeout(builder.timeoutSeconds, TimeUnit.SECONDS)
                .build();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String baseUrl;
        private String apiKey;
        private String appId;
        private String orgId;
        private long timeoutSeconds = DEFAULT_TIMEOUT_SECONDS;

        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        public Builder appId(String appId) {
            this.appId = appId;
            return this;
        }

        public Builder orgId(String orgId) {
            this.orgId = orgId;
            return this;
        }

        public Builder timeout(long seconds) {
            this.timeoutSeconds = seconds;
            return this;
        }

        public TensorWallClient build() {
            return new TensorWallClient(this);
        }
    }

    /**
     * Create a chat completion.
     *
     * @param messages List of messages in the conversation
     * @param model Model to use (e.g., "gpt-4", "claude-3-sonnet")
     * @return ChatCompletionResponse
     */
    public ChatCompletionResponse chat(List<ChatMessage> messages, String model) {
        return chat(messages, model, null, null);
    }

    /**
     * Create a chat completion with options.
     *
     * @param messages List of messages
     * @param model Model to use
     * @param temperature Sampling temperature (0-2)
     * @param maxTokens Maximum tokens to generate
     * @return ChatCompletionResponse
     */
    public ChatCompletionResponse chat(List<ChatMessage> messages, String model,
                                       Double temperature, Integer maxTokens) {
        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model(model)
                .messages(messages)
                .temperature(temperature)
                .maxTokens(maxTokens)
                .appId(appId)
                .build();

        return chat(request);
    }

    /**
     * Create a chat completion with full request object.
     *
     * @param request ChatCompletionRequest
     * @return ChatCompletionResponse
     */
    public ChatCompletionResponse chat(ChatCompletionRequest request) {
        try {
            String json = objectMapper.writeValueAsString(request);
            RequestBody body = RequestBody.create(json, JSON);

            Request httpRequest = new Request.Builder()
                    .url(baseUrl + "/v1/chat/completions")
                    .headers(buildHeaders())
                    .post(body)
                    .build();

            try (Response response = httpClient.newCall(httpRequest).execute()) {
                handleErrorResponse(response);
                String responseBody = response.body().string();
                return objectMapper.readValue(responseBody, ChatCompletionResponse.class);
            }
        } catch (JsonProcessingException e) {
            throw new TensorWallException("Failed to serialize request: " + e.getMessage());
        } catch (IOException e) {
            throw new TensorWallException("Network error: " + e.getMessage());
        }
    }

    /**
     * Create embeddings for text.
     *
     * @param input Text to embed
     * @param model Embedding model to use
     * @return EmbeddingResponse
     */
    public EmbeddingResponse embeddings(String input, String model) {
        EmbeddingRequest request = EmbeddingRequest.builder()
                .model(model)
                .input(input)
                .appId(appId)
                .build();

        return embeddings(request);
    }

    /**
     * Create embeddings for multiple texts.
     *
     * @param inputs List of texts to embed
     * @param model Embedding model to use
     * @return EmbeddingResponse
     */
    public EmbeddingResponse embeddings(List<String> inputs, String model) {
        EmbeddingRequest request = EmbeddingRequest.builder()
                .model(model)
                .input(inputs)
                .appId(appId)
                .build();

        return embeddings(request);
    }

    /**
     * Create embeddings with full request object.
     *
     * @param request EmbeddingRequest
     * @return EmbeddingResponse
     */
    public EmbeddingResponse embeddings(EmbeddingRequest request) {
        try {
            String json = objectMapper.writeValueAsString(request);
            RequestBody body = RequestBody.create(json, JSON);

            Request httpRequest = new Request.Builder()
                    .url(baseUrl + "/v1/embeddings")
                    .headers(buildHeaders())
                    .post(body)
                    .build();

            try (Response response = httpClient.newCall(httpRequest).execute()) {
                handleErrorResponse(response);
                String responseBody = response.body().string();
                return objectMapper.readValue(responseBody, EmbeddingResponse.class);
            }
        } catch (JsonProcessingException e) {
            throw new TensorWallException("Failed to serialize request: " + e.getMessage());
        } catch (IOException e) {
            throw new TensorWallException("Network error: " + e.getMessage());
        }
    }

    /**
     * Check gateway health.
     *
     * @return Health status as Map
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> health() {
        Request request = new Request.Builder()
                .url(baseUrl + "/health")
                .get()
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            String responseBody = response.body().string();
            return objectMapper.readValue(responseBody, Map.class);
        } catch (IOException e) {
            throw new TensorWallException("Network error: " + e.getMessage());
        }
    }

    /**
     * List available models.
     *
     * @return List of model objects
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> models() {
        Request request = new Request.Builder()
                .url(baseUrl + "/v1/models")
                .headers(buildHeaders())
                .get()
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            handleErrorResponse(response);
            String responseBody = response.body().string();
            Map<String, Object> result = objectMapper.readValue(responseBody, Map.class);
            return (List<Map<String, Object>>) result.get("data");
        } catch (IOException e) {
            throw new TensorWallException("Network error: " + e.getMessage());
        }
    }

    private Headers buildHeaders() {
        Headers.Builder builder = new Headers.Builder()
                .add("Content-Type", "application/json")
                .add("Accept", "application/json");

        if (apiKey != null) {
            builder.add("X-API-Key", apiKey);
            builder.add("Authorization", "Bearer " + apiKey);
        }
        if (appId != null) {
            builder.add("X-App-ID", appId);
        }
        if (orgId != null) {
            builder.add("X-Org-ID", orgId);
        }

        return builder.build();
    }

    @SuppressWarnings("unchecked")
    private void handleErrorResponse(Response response) throws IOException {
        if (response.isSuccessful()) {
            return;
        }

        int statusCode = response.code();
        String responseBody = response.body() != null ? response.body().string() : "";

        Map<String, Object> body;
        try {
            body = objectMapper.readValue(responseBody, Map.class);
        } catch (Exception e) {
            body = new HashMap<>();
            body.put("detail", responseBody);
        }

        String message = body.containsKey("detail")
                ? body.get("detail").toString()
                : body.getOrDefault("message", "Unknown error").toString();

        String errorCode = body.getOrDefault("error_code", "").toString();

        // Check for policy/budget errors first (can be 403)
        if (errorCode.toLowerCase().contains("policy") || message.toLowerCase().contains("policy")) {
            String policyName = body.containsKey("policy_name") ? body.get("policy_name").toString() : null;
            throw new PolicyDeniedException(message, statusCode, body, policyName);
        } else if (errorCode.toLowerCase().contains("budget") || message.toLowerCase().contains("budget")) {
            String budgetType = body.containsKey("budget_type") ? body.get("budget_type").toString() : null;
            Double limit = body.containsKey("limit") ? ((Number) body.get("limit")).doubleValue() : null;
            Double current = body.containsKey("current") ? ((Number) body.get("current")).doubleValue() : null;
            throw new BudgetExceededException(message, statusCode, body, budgetType, limit, current);
        } else if (statusCode == 401 || statusCode == 403) {
            throw new AuthenticationException(message, statusCode, body);
        } else if (statusCode == 429) {
            String retryAfter = response.header("Retry-After");
            Integer retryAfterInt = retryAfter != null ? Integer.parseInt(retryAfter) : null;
            throw new RateLimitException(message, statusCode, body, retryAfterInt);
        } else if (statusCode == 400 || statusCode == 422) {
            throw new ValidationException(message, statusCode, body);
        } else if (statusCode >= 500) {
            throw new ServerException(message, statusCode, body);
        } else {
            throw new TensorWallException(message, statusCode, body);
        }
    }

    @Override
    public void close() {
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }
}
