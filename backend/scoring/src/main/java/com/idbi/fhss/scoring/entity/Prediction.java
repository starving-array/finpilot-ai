package com.idbi.fhss.scoring.entity;

import jakarta.persistence.*;
import org.hibernate.type.SqlTypes;
import org.hibernate.annotations.JdbcTypeCode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "prediction")
public class Prediction {

    @Id
    @Column(name = "prediction_id")
    private UUID predictionId;

    @Column(name = "customer_id", nullable = false)
    private UUID customerId;

    @Column(name = "request_id", nullable = false, unique = true)
    private UUID requestId;

    @Column(nullable = false, length = 20)
    private String category;

    @Column(nullable = false)
    @JdbcTypeCode(SqlTypes.JSON)
    private String probabilities;

    @Column(nullable = false)
    private double confidence;

    @Column(name = "model_version", nullable = false, length = 20)
    private String modelVersion;

    @Column(name = "feature_snapshot_id")
    private UUID featureSnapshotId;

    @Column(name = "blank_slate_mode", nullable = false)
    private boolean blankSlateMode;

    @Column(name = "business_rules_applied")
    @JdbcTypeCode(SqlTypes.JSON)
    private String businessRulesApplied;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        if (predictionId == null) predictionId = UUID.randomUUID();
        createdAt = Instant.now();
    }

    public UUID getPredictionId() { return predictionId; }
    public void setPredictionId(UUID predictionId) { this.predictionId = predictionId; }
    public UUID getCustomerId() { return customerId; }
    public void setCustomerId(UUID customerId) { this.customerId = customerId; }
    public UUID getRequestId() { return requestId; }
    public void setRequestId(UUID requestId) { this.requestId = requestId; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public String getProbabilities() { return probabilities; }
    public void setProbabilities(String probabilities) { this.probabilities = probabilities; }
    public double getConfidence() { return confidence; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public String getModelVersion() { return modelVersion; }
    public void setModelVersion(String modelVersion) { this.modelVersion = modelVersion; }
    public UUID getFeatureSnapshotId() { return featureSnapshotId; }
    public void setFeatureSnapshotId(UUID featureSnapshotId) { this.featureSnapshotId = featureSnapshotId; }
    public boolean isBlankSlateMode() { return blankSlateMode; }
    public void setBlankSlateMode(boolean blankSlateMode) { this.blankSlateMode = blankSlateMode; }
    public String getBusinessRulesApplied() { return businessRulesApplied; }
    public void setBusinessRulesApplied(String businessRulesApplied) { this.businessRulesApplied = businessRulesApplied; }
    public Instant getCreatedAt() { return createdAt; }
}
