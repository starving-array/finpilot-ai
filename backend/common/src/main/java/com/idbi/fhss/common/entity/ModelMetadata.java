package com.idbi.fhss.common.entity;

import jakarta.persistence.*;
import org.hibernate.type.SqlTypes;
import org.hibernate.annotations.JdbcTypeCode;
import java.time.Instant;

@Entity
@Table(name = "model_metadata")
public class ModelMetadata {

    @Id
    @Column(name = "model_version", length = 20)
    private String modelVersion;

    @Column(name = "training_date")
    private Instant trainingDate;

    @Column(name = "dataset_hash", length = 64)
    private String datasetHash;

    @JdbcTypeCode(SqlTypes.JSON)
    private String metrics;

    @Column(name = "feature_schema")
    @JdbcTypeCode(SqlTypes.JSON)
    private String featureSchema;

    @Column(name = "artifact_path", length = 500)
    private String artifactPath;

    @Column(name = "deployed_at")
    private Instant deployedAt;

    @Column(name = "deployed_by", length = 100)
    private String deployedBy;

    @Column(nullable = false, length = 20)
    private String status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = Instant.now();
    }

    public String getModelVersion() { return modelVersion; }
    public void setModelVersion(String modelVersion) { this.modelVersion = modelVersion; }
    public Instant getTrainingDate() { return trainingDate; }
    public void setTrainingDate(Instant trainingDate) { this.trainingDate = trainingDate; }
    public String getDatasetHash() { return datasetHash; }
    public void setDatasetHash(String datasetHash) { this.datasetHash = datasetHash; }
    public String getMetrics() { return metrics; }
    public void setMetrics(String metrics) { this.metrics = metrics; }
    public String getFeatureSchema() { return featureSchema; }
    public void setFeatureSchema(String featureSchema) { this.featureSchema = featureSchema; }
    public String getArtifactPath() { return artifactPath; }
    public void setArtifactPath(String artifactPath) { this.artifactPath = artifactPath; }
    public Instant getDeployedAt() { return deployedAt; }
    public void setDeployedAt(Instant deployedAt) { this.deployedAt = deployedAt; }
    public String getDeployedBy() { return deployedBy; }
    public void setDeployedBy(String deployedBy) { this.deployedBy = deployedBy; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Instant getCreatedAt() { return createdAt; }
}
