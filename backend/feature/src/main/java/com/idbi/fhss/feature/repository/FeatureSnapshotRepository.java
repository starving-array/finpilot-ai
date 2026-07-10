package com.idbi.fhss.feature.repository;

import com.idbi.fhss.feature.entity.FeatureSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface FeatureSnapshotRepository extends JpaRepository<FeatureSnapshot, UUID> {
    List<FeatureSnapshot> findByCustomerIdOrderByCreatedAtDesc(UUID customerId);
    Optional<FeatureSnapshot> findTopByCustomerIdOrderByCreatedAtDesc(UUID customerId);
}
