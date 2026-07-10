package com.idbi.fhss.scoring.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public record ScoreResponse(
    String customerId,
    String bucket,
    double probability,
    @JsonProperty("composite_score") double compositeScore,
    Map<String, Double> features,
    Flags flags,
    @JsonProperty("shap_explanation") ShapExplanation shapExplanation,
    @JsonProperty("model_version") String modelVersion,
    String source,
    @JsonProperty("stale_since") Instant staleSince,
    @JsonProperty("request_id") String requestId,
    @JsonProperty("scored_at") Instant scoredAt,
    @JsonProperty("business_name") String businessName,
    @JsonProperty("owner_name") String ownerName,
    @JsonProperty("business_type") String businessType,
    String state,
    @JsonProperty("requested_loan_amount") Double requestedLoanAmount
) {

    public record Flags(
        @JsonProperty("is_blank_slate") boolean isBlankSlate,
        @JsonProperty("epfo_plausibility") EpfoPlausibilityFlag epfoPlausibility,
        @JsonProperty("capacity_flag") CapacityFlag capacityFlag,
        @JsonProperty("seasonality_flags") SeasonalityFlags seasonalityFlags
    ) {}

    public record EpfoPlausibilityFlag(
        String flag,
        String message,
        @JsonProperty("implied_wage") Double impliedWage,
        @JsonProperty("employee_count") Integer employeeCount
    ) {}

    public record CapacityFlag(
        String flag,
        String message,
        @JsonProperty("loan_to_revenue_ratio") Double loanToRevenueRatio,
        String source
    ) {}

    public record SeasonalityFlags(
        SeasonalityFlag fuel,
        SeasonalityFlag electricity
    ) {}

    public record SeasonalityFlag(
        String flag,
        String message,
        Double value,
        @JsonProperty("expected_range") Map<String, Double> expectedRange
    ) {}

    public record ShapExplanation(
        @JsonProperty("shap_values") Map<String, Double> shapValues,
        @JsonProperty("base_value") double baseValue,
        @JsonProperty("feature_ranking") List<FeatureRank> featureRanking,
        @JsonProperty("human_readable_summary") String humanReadableSummary
    ) {}

    public record FeatureRank(
        @JsonProperty("feature_name") String featureName,
        double value,
        @JsonProperty("shap_value") double shapValue,
        int rank,
        String direction,
        @JsonProperty("business_description") String businessDescription,
        String source
    ) {}
}
