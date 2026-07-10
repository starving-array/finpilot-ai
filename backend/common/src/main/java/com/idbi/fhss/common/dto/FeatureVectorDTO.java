package com.idbi.fhss.common.dto;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record FeatureVectorDTO(
    UUID customerId,
    Map<String, Double> features,
    double completenessScore,
    boolean blankSlateMode,
    List<String> validationWarnings,
    String schemaVersion,
    String computationVersion
) {}
