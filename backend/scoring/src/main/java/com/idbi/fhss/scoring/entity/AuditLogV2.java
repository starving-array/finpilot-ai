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
    public Instant getScoredAt() { return scoredAt; }
    public void setScoredAt(Instant scoredAt) { this.scoredAt = scoredAt; }
}
