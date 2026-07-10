package com.idbi.fhss.scoring.repository;

import com.idbi.fhss.scoring.entity.Prediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface PredictionRepository extends JpaRepository<Prediction, UUID> {
    Optional<Prediction> findByRequestId(UUID requestId);
    List<Prediction> findByCustomerIdOrderByCreatedAtDesc(UUID customerId);
}
