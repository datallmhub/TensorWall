package com.tensorwall.sdk.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * A single message in a chat conversation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ChatMessage {
    private String role;
    private String content;
    private String name;

    @JsonProperty("function_call")
    private Map<String, Object> functionCall;

    @JsonProperty("tool_calls")
    private List<Map<String, Object>> toolCalls;

    @JsonProperty("tool_call_id")
    private String toolCallId;

    public ChatMessage() {}

    public ChatMessage(String role, String content) {
        this.role = role;
        this.content = content;
    }

    public static ChatMessage system(String content) {
        return new ChatMessage("system", content);
    }

    public static ChatMessage user(String content) {
        return new ChatMessage("user", content);
    }

    public static ChatMessage assistant(String content) {
        return new ChatMessage("assistant", content);
    }

    // Getters and Setters
    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Map<String, Object> getFunctionCall() {
        return functionCall;
    }

    public void setFunctionCall(Map<String, Object> functionCall) {
        this.functionCall = functionCall;
    }

    public List<Map<String, Object>> getToolCalls() {
        return toolCalls;
    }

    public void setToolCalls(List<Map<String, Object>> toolCalls) {
        this.toolCalls = toolCalls;
    }

    public String getToolCallId() {
        return toolCallId;
    }

    public void setToolCallId(String toolCallId) {
        this.toolCallId = toolCallId;
    }
}
