package com.idbi.fhss.scoring.exception;

public class DuplicateRequestException extends FinancialHealthException {
    private final String requestId;

    public DuplicateRequestException(String requestId) {
        super("DUPLICATE_REQUEST", "Duplicate scoring request: " + requestId);
        this.requestId = requestId;
    }

    public String getRequestId() {
        return requestId;
    }
}
