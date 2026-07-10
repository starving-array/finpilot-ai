package com.idbi.fhss.audit.repository;

import com.idbi.fhss.audit.entity.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {
    List<AuditLog> findByCustomerIdOrderByTimestampDesc(UUID customerId);
    List<AuditLog> findByActionAndTimestampBetween(String action, Instant from, Instant to);
    List<AuditLog> findByCustomerIdAndActionOrderByTimestampDesc(UUID customerId, String action);
}
