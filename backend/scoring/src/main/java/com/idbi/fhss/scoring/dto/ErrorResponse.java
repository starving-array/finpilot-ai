package com.idbi.fhss.scoring.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

public record ErrorResponse(
    String error,
    @JsonProperty("customer_id") String customerId,
    String message,
    Instant timestamp,
    @JsonProperty("retry_after_seconds") Integer retryAfterSeconds
) {}
