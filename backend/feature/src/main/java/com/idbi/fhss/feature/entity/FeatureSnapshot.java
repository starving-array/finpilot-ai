package com.idbi.fhss.feature.entity;

import jakarta.persistence.*;
import org.hibernate.type.SqlTypes;
import org.hibernate.annotations.JdbcTypeCode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "feature_snapshot")
public class FeatureSnapshot {

    @Id
    @Column(name = "snapshot_id")
    private UUID snapshotId;

    @Column(name = "customer_id", nullable = false)
    private UUID customerId;

    @Column(name = "feature_vector", nullable = false)
    @JdbcTypeCode(SqlTypes.JSON)
    private String featureVector;

    @Column(name = "schema_version", nullable = false, length = 20)
    private String schemaVersion;

    @Column(name = "computation_version", nullable = false, length = 20)
    private String computationVersion;

    @Column(name = "completeness_score", nullable = false)
    private double completenessScore;

    @Column(name = "blank_slate_mode", nullable = false)
    private boolean blankSlateMode;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        if (snapshotId == null) snapshotId = UUID.randomUUID();
        createdAt = Instant.now();
    }

    public UUID getSnapshotId() { return snapshotId; }
    public void setSnapshotId(UUID snapshotId) { this.snapshotId = snapshotId; }
    public UUID getCustomerId() { return customerId; }
    public void setCustomerId(UUID customerId) { this.customerId = customerId; }
    public String getFeatureVector() { return featureVector; }
    public void setFeatureVector(String featureVector) { this.featureVector = featureVector; }
    public String getSchemaVersion() { return schemaVersion; }
    public void setSchemaVersion(String schemaVersion) { this.schemaVersion = schemaVersion; }
    public String getComputationVersion() { return computationVersion; }
    public void setComputationVersion(String computationVersion) { this.computationVersion = computationVersion; }
    public double getCompletenessScore() { return completenessScore; }
    public void setCompletenessScore(double completenessScore) { this.completenessScore = completenessScore; }
    public boolean isBlankSlateMode() { return blankSlateMode; }
    public void setBlankSlateMode(boolean blankSlateMode) { this.blankSlateMode = blankSlateMode; }
    public Instant getCreatedAt() { return createdAt; }
}
