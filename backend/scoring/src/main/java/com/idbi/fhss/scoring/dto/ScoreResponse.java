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
    @JsonProperty("requested_loan_amount") Double requestedLoanAmount,
    @JsonProperty("traditional_signal_contribution") double traditionalSignalContribution,
    @JsonProperty("alternative_signal_contribution") double alternativeSignalContribution,
    @JsonProperty("seasonality_adjustment") SeasonalityAdjustment seasonalityAdjustment
) {

    public record Flags(
        @JsonProperty("is_blank_slate") boolean isBlankSlate,
        @JsonProperty("financial_capacity_corroboration") String financialCapacityCorroboration,
        @JsonProperty("financial_capacity_source") String financialCapacitySource,
        @JsonProperty("epfo_plausibility") EpfoPlausibilityFlag epfoPlausibility,
        @JsonProperty("capacity_flag") CapacityFlag capacityFlag,
        @JsonProperty("seasonality_flags") SeasonalityFlags seasonalityFlags
    ) {}

    public record EpfoPlausibilityFlag(
        String flag,
        String message,
        @JsonProperty("implied_wage") Double impliedWage,
        @JsonProperty("employee_count") Integer employeeCount,
        @JsonProperty("contribution_type") String contributionType
    ) {}

    public record CapacityFlag(
        String flag,
        String message,
        @JsonProperty("loan_to_revenue_ratio") Double loanToRevenueRatio,
        String source
    ) {}

    public record SeasonalityFlags(
        @JsonProperty("fuel") SeasonalityFlag fuel
    ) {}

    public record SeasonalityFlag(
        String flag,
        String message,
        Double value,
        @JsonProperty("expected_range") Map<String, Double> expectedRange
    ) {}

    public record SeasonalityAdjustment(
        boolean enabled,
        @JsonProperty("total_penalty_before_cap") double totalPenaltyBeforeCap,
        @JsonProperty("cap_applied") boolean capApplied,
        @JsonProperty("seasonality_adjusted_score") Double seasonalityAdjustedScore,
        @JsonProperty("triggered_metrics") List<SeasonalityTriggeredMetric> triggeredMetrics
    ) {}

    public record SeasonalityTriggeredMetric(
        String metric,
        @JsonProperty("observed_cv") double observedCv,
        @JsonProperty("expected_ceiling") double expectedCeiling,
        @JsonProperty("base_penalty") double basePenalty,
        @JsonProperty("penalty_applied") double penaltyApplied,
        @JsonProperty("peak_month_discount") boolean peakMonthDiscount,
        String reason
    ) {}

    public record ShapExplanation(
        @JsonProperty("shap_values") Map<String, Double> shapValues,
        @JsonProperty("base_value") double baseValue,
        @JsonProperty("feature_ranking") List<FeatureRank> featureRanking,
        @JsonProperty("human_readable_summary") String humanReadableSummary,
        @JsonProperty("traditional_signal_contribution") double traditionalSignalContribution,
        @JsonProperty("alternative_signal_contribution") double alternativeSignalContribution
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
