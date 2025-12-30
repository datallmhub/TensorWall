package com.tensorwall.sdk.exception;

import java.util.Map;

/**
 * Raised when budget limit is exceeded.
 */
public class BudgetExceededException extends TensorWallException {
    private final String budgetType;
    private final Double limit;
    private final Double current;

    public BudgetExceededException(String message, Integer statusCode, Map<String, Object> responseBody,
                                   String budgetType, Double limit, Double current) {
        super(message, statusCode, responseBody);
        this.budgetType = budgetType;
        this.limit = limit;
        this.current = current;
    }

    public String getBudgetType() {
        return budgetType;
    }

    public Double getLimit() {
        return limit;
    }

    public Double getCurrent() {
        return current;
    }
}
