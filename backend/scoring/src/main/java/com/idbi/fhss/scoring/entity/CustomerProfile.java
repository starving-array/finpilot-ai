package com.idbi.fhss.scoring.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "customer_profile")
public class CustomerProfile {

    @Id
    @Column(name = "customer_id", length = 20)
    private String customerId;

    @Column(name = "business_name", length = 200, nullable = false)
    private String businessName;

    @Column(name = "owner_name", length = 200)
    private String ownerName;

    @Column(name = "business_type", length = 50, nullable = false)
    private String businessType;

    @Column(length = 50)
    private String state;

    @Column(name = "years_in_operation", precision = 4, scale = 1)
    private BigDecimal yearsInOperation;

    @Column(name = "gst_registered", nullable = false)
    private boolean gstRegistered;

    @Column(name = "gst_monthly_turnover_avg", precision = 14, scale = 2)
    private BigDecimal gstMonthlyTurnoverAvg;

    @Column(name = "gst_filing_regularity", precision = 3, scale = 2)
    private BigDecimal gstFilingRegularity;

    @Column(name = "upi_monthly_txn_count")
    private Integer upiMonthlyTxnCount;

    @Column(name = "upi_monthly_txn_value", precision = 14, scale = 2)
    private BigDecimal upiMonthlyTxnValue;

    @Column(name = "electricity_monthly_units_avg", precision = 10, scale = 2)
    private BigDecimal electricityMonthlyUnitsAvg;

    @Column(name = "electricity_payment_delay_days_avg", precision = 6, scale = 2)
    private BigDecimal electricityPaymentDelayDaysAvg;

    @Column(name = "epfo_contribution_regularity", precision = 3, scale = 2)
    private BigDecimal epfoContributionRegularity;

    @Column(name = "epfo_employee_count")
    private Integer epfoEmployeeCount;

    @Column(name = "epfo_contribution_amount", precision = 14, scale = 2)
    private BigDecimal epfoContributionAmount;

    @Column(name = "water_monthly_consumption_kl", precision = 10, scale = 2)
    private BigDecimal waterMonthlyConsumptionKl;

    @Column(name = "water_payment_delay_days_avg", precision = 6, scale = 2)
    private BigDecimal waterPaymentDelayDaysAvg;

    @Column(name = "fuel_monthly_spend_avg", precision = 14, scale = 2)
    private BigDecimal fuelMonthlySpendAvg;

    @Column(name = "fuel_spend_volatility", precision = 5, scale = 2)
    private BigDecimal fuelSpendVolatility;

    @Column(name = "requested_loan_amount", precision = 14, scale = 2)
    private BigDecimal requestedLoanAmount;

    @Column(name = "is_blank_slate", nullable = false)
    private boolean blankSlate;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getBusinessName() { return businessName; }
    public void setBusinessName(String businessName) { this.businessName = businessName; }
    public String getOwnerName() { return ownerName; }
    public void setOwnerName(String ownerName) { this.ownerName = ownerName; }
    public String getBusinessType() { return businessType; }
    public void setBusinessType(String businessType) { this.businessType = businessType; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public BigDecimal getYearsInOperation() { return yearsInOperation; }
    public void setYearsInOperation(BigDecimal yearsInOperation) { this.yearsInOperation = yearsInOperation; }
    public boolean isGstRegistered() { return gstRegistered; }
    public void setGstRegistered(boolean gstRegistered) { this.gstRegistered = gstRegistered; }
    public BigDecimal getGstMonthlyTurnoverAvg() { return gstMonthlyTurnoverAvg; }
    public void setGstMonthlyTurnoverAvg(BigDecimal gstMonthlyTurnoverAvg) { this.gstMonthlyTurnoverAvg = gstMonthlyTurnoverAvg; }
    public BigDecimal getGstFilingRegularity() { return gstFilingRegularity; }
    public void setGstFilingRegularity(BigDecimal gstFilingRegularity) { this.gstFilingRegularity = gstFilingRegularity; }
    public Integer getUpiMonthlyTxnCount() { return upiMonthlyTxnCount; }
    public void setUpiMonthlyTxnCount(Integer upiMonthlyTxnCount) { this.upiMonthlyTxnCount = upiMonthlyTxnCount; }
    public BigDecimal getUpiMonthlyTxnValue() { return upiMonthlyTxnValue; }
    public void setUpiMonthlyTxnValue(BigDecimal upiMonthlyTxnValue) { this.upiMonthlyTxnValue = upiMonthlyTxnValue; }
    public BigDecimal getElectricityMonthlyUnitsAvg() { return electricityMonthlyUnitsAvg; }
    public void setElectricityMonthlyUnitsAvg(BigDecimal electricityMonthlyUnitsAvg) { this.electricityMonthlyUnitsAvg = electricityMonthlyUnitsAvg; }
    public BigDecimal getElectricityPaymentDelayDaysAvg() { return electricityPaymentDelayDaysAvg; }
    public void setElectricityPaymentDelayDaysAvg(BigDecimal electricityPaymentDelayDaysAvg) { this.electricityPaymentDelayDaysAvg = electricityPaymentDelayDaysAvg; }
    public BigDecimal getEpfoContributionRegularity() { return epfoContributionRegularity; }
    public void setEpfoContributionRegularity(BigDecimal epfoContributionRegularity) { this.epfoContributionRegularity = epfoContributionRegularity; }
    public Integer getEpfoEmployeeCount() { return epfoEmployeeCount; }
    public void setEpfoEmployeeCount(Integer epfoEmployeeCount) { this.epfoEmployeeCount = epfoEmployeeCount; }
    public BigDecimal getEpfoContributionAmount() { return epfoContributionAmount; }
    public void setEpfoContributionAmount(BigDecimal epfoContributionAmount) { this.epfoContributionAmount = epfoContributionAmount; }
    public BigDecimal getWaterMonthlyConsumptionKl() { return waterMonthlyConsumptionKl; }
    public void setWaterMonthlyConsumptionKl(BigDecimal waterMonthlyConsumptionKl) { this.waterMonthlyConsumptionKl = waterMonthlyConsumptionKl; }
    public BigDecimal getWaterPaymentDelayDaysAvg() { return waterPaymentDelayDaysAvg; }
    public void setWaterPaymentDelayDaysAvg(BigDecimal waterPaymentDelayDaysAvg) { this.waterPaymentDelayDaysAvg = waterPaymentDelayDaysAvg; }
    public BigDecimal getFuelMonthlySpendAvg() { return fuelMonthlySpendAvg; }
    public void setFuelMonthlySpendAvg(BigDecimal fuelMonthlySpendAvg) { this.fuelMonthlySpendAvg = fuelMonthlySpendAvg; }
    public BigDecimal getFuelSpendVolatility() { return fuelSpendVolatility; }
    public void setFuelSpendVolatility(BigDecimal fuelSpendVolatility) { this.fuelSpendVolatility = fuelSpendVolatility; }
    public BigDecimal getRequestedLoanAmount() { return requestedLoanAmount; }
    public void setRequestedLoanAmount(BigDecimal requestedLoanAmount) { this.requestedLoanAmount = requestedLoanAmount; }
    public boolean isBlankSlate() { return blankSlate; }
    public void setBlankSlate(boolean blankSlate) { this.blankSlate = blankSlate; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
