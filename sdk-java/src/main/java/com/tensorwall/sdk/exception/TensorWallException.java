package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Base exception for TensorWall SDK.
 */
public class TensorWallException extends RuntimeException {
    private final Integer statusCode;
    private final Map<String, Object> responseBody;

    public TensorWallException(String message) {
        this(message, null, null);
    }

    public TensorWallException(String message, Integer statusCode) {
        this(message, statusCode, null);
    }

    public TensorWallException(String message, Integer statusCode, Map<String, Object> responseBody) {
        super(message);
        this.statusCode = statusCode;
        this.responseBody = responseBody;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public Map<String, Object> getResponseBody() {
        return responseBody;
    }

    @Override
    public String toString() {
        if (statusCode != null) {
            return String.format("[%d] %s", statusCode, getMessage());
        }
        return getMessage();
    }
}
