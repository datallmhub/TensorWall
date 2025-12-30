package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when request validation fails (400/422).
 */
public class ValidationException extends TensorWallException {
    public ValidationException(String message, Integer statusCode, Map<String, Object> responseBody) {
        super(message, statusCode, responseBody);
    }
}
