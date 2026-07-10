package com.idbi.fhss.scoring.exception;

public class ScoringServiceTimeoutException extends FinancialHealthException {
    public ScoringServiceTimeoutException(String message) {
        super("SCORING_TIMEOUT", message);
    }

    public ScoringServiceTimeoutException(String customerId, long timeoutMs) {
        super("SCORING_TIMEOUT", "ML service timed out after " + timeoutMs + "ms for customer " + customerId);
    }
}
