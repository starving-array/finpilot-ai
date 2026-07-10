package com.idbi.fhss.scoring.repository;

import com.idbi.fhss.scoring.entity.UnderwriterDecision;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface UnderwriterDecisionRepository extends JpaRepository<UnderwriterDecision, Long> {
    List<UnderwriterDecision> findByCustomerIdOrderByCreatedAtDesc(String customerId);
    List<UnderwriterDecision> findByDecisionOrderByCreatedAtDesc(String decision);
}
