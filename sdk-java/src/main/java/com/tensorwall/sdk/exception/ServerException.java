package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when server returns an error (5xx).
 */
public class ServerException extends TensorWallException {
    public ServerException(String message, Integer statusCode, Map<String, Object> responseBody) {
        super(message, statusCode, responseBody);
    }
}
