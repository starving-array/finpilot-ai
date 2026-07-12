package com.idbi.fhss.scoring.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "audit_log_v2")
public class AuditLogV2 {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "customer_id", length = 20, nullable = false)
    private String customerId;

    @Column(length = 20, nullable = false)
    private String bucket;

    @Column(precision = 5, scale = 4)
    private BigDecimal confidence;

    @Column(name = "blank_slate_flag", nullable = false)
    private boolean blankSlateFlag;

    @Column(name = "model_version", length = 50, nullable = false)
    private String modelVersion;

    @Column(name = "shap_reasons", nullable = false)
    @JdbcTypeCode(SqlTypes.JSON)
    private String shapReasons;

    @Column(name = "capacity_flag")
    @JdbcTypeCode(SqlTypes.JSON)
    private String capacityFlag;

    @Column(name = "epfo_flag")
    @JdbcTypeCode(SqlTypes.JSON)
    private String epfoFlag;

    @Column(name = "seasonality_flags")
    @JdbcTypeCode(SqlTypes.JSON)
    private String seasonalityFlags;

    @Column(length = 20, nullable = false)
    private String source;

    @Column(name = "composite_score", precision = 5, scale = 4)
    private BigDecimal compositeScore;

    @Column(name = "features")
    @JdbcTypeCode(SqlTypes.JSON)
    private String features;

    @Column(name = "request_id", length = 16)
    private String requestId;

    @Column(name = "business_name", length = 200)
    private String businessName;

    @Column(name = "owner_name", length = 200)
    private String ownerName;

    @Column(name = "business_type", length = 50)
    private String businessType;

    @Column(length = 50)
    private String state;

    @Column(name = "requested_loan_amount", precision = 14, scale = 2)
    private BigDecimal requestedLoanAmount;

    @Column(name = "scored_at", nullable = false, updatable = false)
    private Instant scoredAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getBucket() { return bucket; }
    public void setBucket(String bucket) { this.bucket = bucket; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public boolean isBlankSlateFlag() { return blankSlateFlag; }
    public void setBlankSlateFlag(boolean blankSlateFlag) { this.blankSlateFlag = blankSlateFlag; }
    public String getModelVersion() { return modelVersion; }
    public void setModelVersion(String modelVersion) { this.modelVersion = modelVersion; }
    public String getShapReasons() { return shapReasons; }
    public void setShapReasons(String shapReasons) { this.shapReasons = shapReasons; }
    public String getCapacityFlag() { return capacityFlag; }
    public void setCapacityFlag(String capacityFlag) { this.capacityFlag = capacityFlag; }
    public String getEpfoFlag() { return epfoFlag; }
    public void setEpfoFlag(String epfoFlag) { this.epfoFlag = epfoFlag; }
    public String getSeasonalityFlags() { return seasonalityFlags; }
    public void setSeasonalityFlags(String seasonalityFlags) { this.seasonalityFlags = seasonalityFlags; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public BigDecimal getCompositeScore() { return compositeScore; }
    public void setCompositeScore(BigDecimal compositeScore) { this.compositeScore = compositeScore; }
    public String getFeatures() { return features; }
    public void setFeatures(String features) { this.features = features; }
    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getBusinessName() { return businessName; }
    public void setBusinessName(String businessName) { this.businessName = businessName; }
    public String getOwnerName() { return ownerName; }
    public void setOwnerName(String ownerName) { this.ownerName = ownerName; }
    public String getBusinessType() { return businessType; }
    public void setBusinessType(String businessType) { this.businessType = businessType; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public BigDecimal getRequestedLoanAmount() { return requestedLoanAmount; }
    public void setRequestedLoanAmount(BigDecimal requestedLoanAmount) { this.requestedLoanAmount = requestedLoanAmount; }
    public Instant getScoredAt() { return scoredAt; }
    public void setScoredAt(Instant scoredAt) { this.scoredAt = scoredAt; }
}
