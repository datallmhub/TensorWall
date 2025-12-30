package com.tensorwall.sdk.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Request for embeddings.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EmbeddingRequest {
    private String model;
    private Object input; // String or List<String>

    @JsonProperty("encoding_format")
    private String encodingFormat;

    private Integer dimensions;
    private String user;

    // TensorWall specific
    @JsonProperty("app_id")
    private String appId;

    private String feature;

    @JsonProperty("dry_run")
    private Boolean dryRun;

    public EmbeddingRequest() {}

    public EmbeddingRequest(String model, String input) {
        this.model = model;
        this.input = input;
    }

    public EmbeddingRequest(String model, List<String> input) {
        this.model = model;
        this.input = input;
    }

    // Builder pattern
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final EmbeddingRequest request = new EmbeddingRequest();

        public Builder model(String model) {
            request.model = model;
            return this;
        }

        public Builder input(String input) {
            request.input = input;
            return this;
        }

        public Builder input(List<String> input) {
            request.input = input;
            return this;
        }

        public Builder encodingFormat(String encodingFormat) {
            request.encodingFormat = encodingFormat;
            return this;
        }

        public Builder dimensions(Integer dimensions) {
            request.dimensions = dimensions;
            return this;
        }

        public Builder appId(String appId) {
            request.appId = appId;
            return this;
        }

        public EmbeddingRequest build() {
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

    public Object getInput() {
        return input;
    }

    public void setInput(Object input) {
        this.input = input;
    }

    public String getEncodingFormat() {
        return encodingFormat;
    }

    public void setEncodingFormat(String encodingFormat) {
        this.encodingFormat = encodingFormat;
    }

    public Integer getDimensions() {
        return dimensions;
    }

    public void setDimensions(Integer dimensions) {
        this.dimensions = dimensions;
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
