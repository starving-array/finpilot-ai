package com.idbi.fhss.scoring.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record DecisionRequest(
    @JsonProperty("customer_id") String customerId,
    String decision,
    String remarks
) {}
