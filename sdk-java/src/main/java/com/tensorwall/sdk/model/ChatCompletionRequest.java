package com.tensorwall.sdk.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Request for chat completion.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ChatCompletionRequest {
    private String model;
    private List<ChatMessage> messages;
    private Double temperature;

    @JsonProperty("max_tokens")
    private Integer maxTokens;

    @JsonProperty("top_p")
    private Double topP;

    @JsonProperty("frequency_penalty")
    private Double frequencyPenalty;

    @JsonProperty("presence_penalty")
    private Double presencePenalty;

    private Object stop;
    private Boolean stream;
    private List<Map<String, Object>> tools;

    @JsonProperty("tool_choice")
    private Object toolChoice;

    @JsonProperty("response_format")
    private Map<String, String> responseFormat;

    private Integer seed;
    private String user;

    // TensorWall specific
    @JsonProperty("app_id")
    private String appId;

    private String feature;

    @JsonProperty("dry_run")
    private Boolean dryRun;

    public ChatCompletionRequest() {}

    public ChatCompletionRequest(String model, List<ChatMessage> messages) {
        this.model = model;
        this.messages = messages;
    }

    // Builder pattern
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final ChatCompletionRequest request = new ChatCompletionRequest();

        public Builder model(String model) {
            request.model = model;
            return this;
        }

        public Builder messages(List<ChatMessage> messages) {
            request.messages = messages;
            return this;
        }

        public Builder temperature(Double temperature) {
            request.temperature = temperature;
            return this;
        }

        public Builder maxTokens(Integer maxTokens) {
            request.maxTokens = maxTokens;
            return this;
        }

        public Builder topP(Double topP) {
            request.topP = topP;
            return this;
        }

        public Builder stream(Boolean stream) {
            request.stream = stream;
            return this;
        }

        public Builder tools(List<Map<String, Object>> tools) {
            request.tools = tools;
            return this;
        }

        public Builder appId(String appId) {
            request.appId = appId;
            return this;
        }

        public Builder feature(String feature) {
            request.feature = feature;
            return this;
        }

        public Builder dryRun(Boolean dryRun) {
            request.dryRun = dryRun;
            return this;
        }

        public ChatCompletionRequest build() {
            return request;
        }
    }

    // Getters and Setters
    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public List<ChatMessage> getMessages() {
        return messages;
    }

    public void setMessages(List<ChatMessage> messages) {
        this.messages = messages;
    }

    public Double getTemperature() {
        return temperature;
    }

    public void setTemperature(Double temperature) {
        this.temperature = temperature;
    }

    public Integer getMaxTokens() {
        return maxTokens;
    }

    public void setMaxTokens(Integer maxTokens) {
        this.maxTokens = maxTokens;
    }

    public Double getTopP() {
        return topP;
    }

    public void setTopP(Double topP) {
        this.topP = topP;
    }

    public Double getFrequencyPenalty() {
        return frequencyPenalty;
    }

    public void setFrequencyPenalty(Double frequencyPenalty) {
        this.frequencyPenalty = frequencyPenalty;
    }

    public Double getPresencePenalty() {
        return presencePenalty;
    }

    public void setPresencePenalty(Double presencePenalty) {
        this.presencePenalty = presencePenalty;
    }

    public Object getStop() {
        return stop;
    }

    public void setStop(Object stop) {
        this.stop = stop;
    }

    public Boolean getStream() {
        return stream;
    }

    public void setStream(Boolean stream) {
        this.stream = stream;
    }

    public List<Map<String, Object>> getTools() {
        return tools;
    }

    public void setTools(List<Map<String, Object>> tools) {
        this.tools = tools;
    }

    public Object getToolChoice() {
        return toolChoice;
    }

    public void setToolChoice(Object toolChoice) {
        this.toolChoice = toolChoice;
    }

    public Map<String, String> getResponseFormat() {
        return responseFormat;
    }

    public void setResponseFormat(Map<String, String> responseFormat) {
        this.responseFormat = responseFormat;
    }

    public Integer getSeed() {
        return seed;
    }

    public void setSeed(Integer seed) {
        this.seed = seed;
    }

    public String getUser() {
        return user;
    }

    public void setUser(String user) {
        this.user = user;
    }

    public String getAppId() {
        return appId;
    }

    public void setAppId(String appId) {
        this.appId = appId;
    }

    public String getFeature() {
        return feature;
    }

    public void setFeature(String feature) {
        this.feature = feature;
    }

    public Boolean getDryRun() {
        return dryRun;
    }

    public void setDryRun(Boolean dryRun) {
        this.dryRun = dryRun;
    }
}
