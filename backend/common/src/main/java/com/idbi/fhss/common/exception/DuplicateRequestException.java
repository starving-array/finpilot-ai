package com.idbi.fhss.common.exception;

public class DuplicateRequestException extends RuntimeException {
    public DuplicateRequestException(String requestId) {
        super("Duplicate request detected: " + requestId);
    }
}
