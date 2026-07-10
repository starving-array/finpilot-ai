package com.idbi.fhss.scoring;

import com.idbi.fhss.scoring.exception.*;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleCustomerNotFound_shouldReturn404() {
        var ex = new CustomerNotFoundException("CUST99999");

        var response = handler.handleCustomerNotFound(ex);

        assertEquals(404, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("CUSTOMER_NOT_FOUND", body.get("error"));
        assertEquals("CUST99999", body.get("customerId"));
    }

    @Test
    void handleInvalidProfile_shouldReturn422() {
        var ex = new InvalidProfileDataException("Missing required fields");

        var response = handler.handleInvalidProfile(ex);

        assertEquals(422, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("INVALID_PROFILE_DATA", body.get("error"));
    }

    @Test
    void handleServiceUnavailable_shouldReturn503() {
        var ex = new ScoringServiceUnavailableException("ML service is down", 45);

        var response = handler.handleServiceUnavailable(ex);

        assertEquals(503, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("SCORING_UNAVAILABLE", body.get("error"));
        assertEquals(45, body.get("retryAfterSeconds"));
    }

    @Test
    void handleServiceUnavailable_shouldUseDefaultRetry() {
        var ex = new ScoringServiceUnavailableException("Down");

        var response = handler.handleServiceUnavailable(ex);

        var body = (Map<String, Object>) response.getBody();
        assertEquals(30, body.get("retryAfterSeconds"));
    }

    @Test
    void handleServiceTimeout_shouldReturn504() {
        var ex = new ScoringServiceTimeoutException("CUST00001", 10000);

        var response = handler.handleServiceTimeout(ex);

        assertEquals(504, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("SCORING_TIMEOUT", body.get("error"));
    }

    @Test
    void handleDuplicate_shouldReturn409() {
        var ex = new DuplicateRequestException("req-123");

        var response = handler.handleDuplicate(ex);

        assertEquals(409, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("DUPLICATE_REQUEST", body.get("error"));
        assertEquals("req-123", body.get("message"));
    }

    @Test
    void handleAuditError_shouldReturn500() {
        var ex = new AuditPersistenceException("DB write failed", new RuntimeException("cause"));

        var response = handler.handleAuditError(ex);

        assertEquals(500, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("INTERNAL_ERROR", body.get("error"));
    }

    @Test
    void handleGeneric_shouldReturn500() {
        var ex = new RuntimeException("Unexpected error");

        var response = handler.handleGeneric(ex);

        assertEquals(500, response.getStatusCode().value());
        var body = (Map<String, Object>) response.getBody();
        assertEquals("INTERNAL_ERROR", body.get("error"));
    }
}
