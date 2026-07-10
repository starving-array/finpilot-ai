package com.idbi.fhss.scoring.exception;

public abstract class FinancialHealthException extends RuntimeException {
    private final String errorCode;

    protected FinancialHealthException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    protected FinancialHealthException(String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String getErrorCode() {
        return errorCode;
    }
}
