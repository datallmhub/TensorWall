package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when request is denied by policy engine.
 */
public class PolicyDeniedException extends TensorWallException {
    private final String policyName;

    public PolicyDeniedException(String message, Integer statusCode, Map<String, Object> responseBody, String policyName) {
        super(message, statusCode, responseBody);
        this.policyName = policyName;
    }

    public String getPolicyName() {
        return policyName;
    }
}
