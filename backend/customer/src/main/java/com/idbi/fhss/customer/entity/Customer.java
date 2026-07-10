package com.idbi.fhss.customer.entity;

import jakarta.persistence.*;
import org.hibernate.type.SqlTypes;
import org.hibernate.annotations.JdbcTypeCode;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Entity
@Table(name = "customer")
public class Customer {

    @Id
    @Column(name = "customer_id")
    private UUID customerId;

    @Column(nullable = false, length = 10)
    private String pan;

    @Column(length = 21)
    private String cin;

    @Column(nullable = false)
    private String name;

    @Column(name = "kyc_status", nullable = false, length = 20)
    private String kycStatus;

    @Column(name = "traditional_data")
    @JdbcTypeCode(SqlTypes.JSON)
    private String traditionalData;

    @Column(name = "alternative_data")
    @JdbcTypeCode(SqlTypes.JSON)
    private String alternativeData;

    @Version
    @Column(nullable = false)
    private int version;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "deleted_at")
    private Instant deletedAt;

    @PrePersist
    protected void onCreate() {
        if (customerId == null) {
            customerId = UUID.randomUUID();
        }
        var now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = Instant.now();
    }

    public UUID getCustomerId() { return customerId; }
    public void setCustomerId(UUID customerId) { this.customerId = customerId; }
    public String getPan() { return pan; }
    public void setPan(String pan) { this.pan = pan; }
    public String getCin() { return cin; }
    public void setCin(String cin) { this.cin = cin; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getKycStatus() { return kycStatus; }
    public void setKycStatus(String kycStatus) { this.kycStatus = kycStatus; }
    public String getTraditionalData() { return traditionalData; }
    public void setTraditionalData(String traditionalData) { this.traditionalData = traditionalData; }
    public String getAlternativeData() { return alternativeData; }
    public void setAlternativeData(String alternativeData) { this.alternativeData = alternativeData; }
    public int getVersion() { return version; }
    public void setVersion(int version) { this.version = version; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public Instant getDeletedAt() { return deletedAt; }
    public void setDeletedAt(Instant deletedAt) { this.deletedAt = deletedAt; }
}
