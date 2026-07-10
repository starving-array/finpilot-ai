package com.idbi.fhss.scoring.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CustomerProfileResponse(
    @JsonProperty("customer_id") String customerId,
    @JsonProperty("business_name") String businessName,
    @JsonProperty("owner_name") String ownerName,
    @JsonProperty("business_type") String businessType,
    String state,
    @JsonProperty("years_in_operation") Double yearsInOperation,
    @JsonProperty("requested_loan_amount") Double requestedLoanAmount,
    @JsonProperty("is_blank_slate") boolean blankSlate,
    @JsonProperty("data_completeness") Double dataCompleteness
) {}
