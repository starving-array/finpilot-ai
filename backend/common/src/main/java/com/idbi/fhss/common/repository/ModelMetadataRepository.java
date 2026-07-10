package com.idbi.fhss.common.repository;

import com.idbi.fhss.common.entity.ModelMetadata;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ModelMetadataRepository extends JpaRepository<ModelMetadata, String> {
    Optional<ModelMetadata> findTopByStatusOrderByCreatedAtDesc(String status);
}
