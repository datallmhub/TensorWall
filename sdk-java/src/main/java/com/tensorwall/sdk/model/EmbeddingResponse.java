package com.tensorwall.sdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Response from embeddings.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EmbeddingResponse {
    private String object;
    private List<EmbeddingData> data;
    private String model;
    private Usage usage;

    // TensorWall metadata
    @JsonProperty("request_id")
    private String requestId;

    private Double cost;

    @JsonProperty("latency_ms")
    private Double latencyMs;

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class EmbeddingData {
        private String object;
        private List<Double> embedding;
        private Integer index;

        public String getObject() {
            return object;
        }

        public void setObject(String object) {
            this.object = object;
        }

        public List<Double> getEmbedding() {
            return embedding;
        }

        public void setEmbedding(List<Double> embedding) {
            this.embedding = embedding;
        }

        public Integer getIndex() {
            return index;
        }

        public void setIndex(Integer index) {
            this.index = index;
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Usage {
        @JsonProperty("prompt_tokens")
        private Integer promptTokens;

        @JsonProperty("total_tokens")
        private Integer totalTokens;

        public Integer getPromptTokens() {
            return promptTokens;
        }

        public void setPromptTokens(Integer promptTokens) {
            this.promptTokens = promptTokens;
        }

        public Integer getTotalTokens() {
            return totalTokens;
        }

        public void setTotalTokens(Integer totalTokens) {
            this.totalTokens = totalTokens;
        }
    }

    // Convenience method
    public List<Double> getFirstEmbedding() {
        if (data != null && !data.isEmpty()) {
            return data.get(0).getEmbedding();
        }
        return null;
    }

    // Getters and Setters
    public String getObject() {
        return object;
    }

    public void setObject(String object) {
        this.object = object;
    }

    public List<EmbeddingData> getData() {
        return data;
    }

    public void setData(List<EmbeddingData> data) {
        this.data = data;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public Usage getUsage() {
        return usage;
    }

    public void setUsage(Usage usage) {
        this.usage = usage;
    }

    public String getRequestId() {
        return requestId;
    }

    public void setRequestId(String requestId) {
        this.requestId = requestId;
    }

    public Double getCost() {
        return cost;
    }

    public void setCost(Double cost) {
        this.cost = cost;
    }

    public Double getLatencyMs() {
        return latencyMs;
    }

    public void setLatencyMs(Double latencyMs) {
        this.latencyMs = latencyMs;
    }
}
