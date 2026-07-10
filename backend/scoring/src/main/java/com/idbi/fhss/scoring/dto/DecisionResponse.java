package com.idbi.fhss.scoring.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record DecisionResponse(
    Long id,
    @JsonProperty("customer_id") String customerId,
    String decision,
    String remarks,
    String reviewer,
    @JsonProperty("created_at") Instant createdAt
) {}
