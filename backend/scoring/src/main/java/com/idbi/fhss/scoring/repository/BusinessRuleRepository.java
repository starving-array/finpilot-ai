package com.idbi.fhss.scoring.repository;

import com.idbi.fhss.scoring.entity.BusinessRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface BusinessRuleRepository extends JpaRepository<BusinessRule, UUID> {
    List<BusinessRule> findByEnabledTrueOrderByPriorityDesc();
}
