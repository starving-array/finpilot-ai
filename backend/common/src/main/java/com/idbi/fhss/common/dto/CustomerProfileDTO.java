package com.idbi.fhss.common.dto;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public record CustomerProfileDTO(
    UUID customerId,
    String pan,
    String cin,
    String name,
    String kycStatus,
    Map<String, Object> traditionalData,
    Map<String, Object> alternativeData,
    int version,
    Instant createdAt,
    Instant updatedAt
) {}
