package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when authentication fails (401/403).
 */
public class AuthenticationException extends TensorWallException {
    public AuthenticationException(String message, Integer statusCode, Map<String, Object> responseBody) {
        super(message, statusCode, responseBody);
    }
}
