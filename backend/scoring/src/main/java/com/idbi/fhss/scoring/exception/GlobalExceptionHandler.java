package com.idbi.fhss.scoring.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import java.time.Instant;
import java.util.Map;

@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(CustomerNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleCustomerNotFound(CustomerNotFoundException ex) {
        log.warn("Customer not found: {}", ex.getCustomerId());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
            "error", "CUSTOMER_NOT_FOUND",
            "customerId", ex.getCustomerId(),
            "message", ex.getMessage(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(InvalidProfileDataException.class)
    public ResponseEntity<Map<String, Object>> handleInvalidProfile(InvalidProfileDataException ex) {
        log.warn("Invalid profile data: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(Map.of(
            "error", "INVALID_PROFILE_DATA",
            "message", ex.getMessage(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(ScoringServiceUnavailableException.class)
    public ResponseEntity<Map<String, Object>> handleServiceUnavailable(ScoringServiceUnavailableException ex) {
        log.warn("Scoring service unavailable: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(Map.of(
            "error", "SCORING_UNAVAILABLE",
            "message", ex.getMessage(),
            "retryAfterSeconds", ex.getRetryAfterSeconds(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(ScoringServiceTimeoutException.class)
    public ResponseEntity<Map<String, Object>> handleServiceTimeout(ScoringServiceTimeoutException ex) {
        log.warn("Scoring service timeout: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT).body(Map.of(
            "error", "SCORING_TIMEOUT",
            "message", ex.getMessage(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(DuplicateRequestException.class)
    public ResponseEntity<Map<String, Object>> handleDuplicate(DuplicateRequestException ex) {
        log.warn("Duplicate request: {}", ex.getRequestId());
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
            "error", "DUPLICATE_REQUEST",
            "message", ex.getMessage(),
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(AuditPersistenceException.class)
    public ResponseEntity<Map<String, Object>> handleAuditError(AuditPersistenceException ex) {
        log.error("Audit persistence failed: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
            "error", "INTERNAL_ERROR",
            "message", "An internal error occurred",
            "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneric(Exception ex) {
        log.error("Unhandled exception", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
            "error", "INTERNAL_ERROR",
            "message", "An unexpected error occurred",
            "timestamp", Instant.now().toString()
        ));
    }
}
