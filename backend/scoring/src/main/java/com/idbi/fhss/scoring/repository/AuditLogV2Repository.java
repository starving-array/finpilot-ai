package com.idbi.fhss.scoring.repository;

import com.idbi.fhss.scoring.entity.AuditLogV2;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditLogV2Repository extends JpaRepository<AuditLogV2, Long> {
    List<AuditLogV2> findByCustomerIdOrderByScoredAtDesc(String customerId);
}
