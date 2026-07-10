package com.idbi.fhss.scoring.exception;

public class ScoringServiceUnavailableException extends FinancialHealthException {
    private final int retryAfterSeconds;

    public ScoringServiceUnavailableException(String message) {
        super("SCORING_UNAVAILABLE", message);
        this.retryAfterSeconds = 30;
    }

    public ScoringServiceUnavailableException(String message, int retryAfterSeconds) {
        super("SCORING_UNAVAILABLE", message);
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public int getRetryAfterSeconds() {
        return retryAfterSeconds;
    }
}
