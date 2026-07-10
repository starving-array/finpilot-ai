package com.idbi.fhss.common.dto;

import com.idbi.fhss.common.enums.ConfidenceBand;
import com.idbi.fhss.common.enums.FinancialHealthCategory;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record PredictionResponse(
    UUID customerId,
    UUID requestId,
    FinancialHealthCategory category,
    Map<FinancialHealthCategory, Double> probabilities,
    double confidence,
    ConfidenceBand confidenceBand,
    String modelVersion,
    boolean blankSlateMode,
    List<String> businessRulesApplied,
    ShapExplanation shapExplanation,
    String underwriterNotes,
    boolean degradedMode,
    String aiNarrativeExplanation,
    Instant createdAt
) {

    public record ShapExplanation(
        Map<String, Double> shapValues,
        double baseValue,
        List<FeatureRank> featureRanking,
        String humanReadableSummary
    ) {}

    public record FeatureRank(
        String featureName,
        double value,
        double shapValue,
        int rank,
        String direction,
        String businessDescription
    ) {}
}
