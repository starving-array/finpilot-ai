package com.idbi.fhss.scoring.exception;

public class AuditPersistenceException extends FinancialHealthException {
    public AuditPersistenceException(String message, Throwable cause) {
        super("AUDIT_PERSISTENCE_ERROR", "Failed to persist audit record: " + message, cause);
    }
}
