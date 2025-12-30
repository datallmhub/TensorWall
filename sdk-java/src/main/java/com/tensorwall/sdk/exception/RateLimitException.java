package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when rate limit is exceeded (429).
 */
public class RateLimitException extends TensorWallException {
    private final Integer retryAfter;

    public RateLimitException(String message, Integer statusCode, Map<String, Object> responseBody, Integer retryAfter) {
        super(message, statusCode, responseBody);
        this.retryAfter = retryAfter;
    }

    public Integer getRetryAfter() {
        return retryAfter;
    }
}
