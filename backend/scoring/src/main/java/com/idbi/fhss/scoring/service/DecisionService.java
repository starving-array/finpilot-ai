package com.idbi.fhss.scoring.service;

import com.idbi.fhss.scoring.dto.DecisionRequest;
import com.idbi.fhss.scoring.dto.DecisionResponse;
import com.idbi.fhss.scoring.entity.UnderwriterDecision;
import com.idbi.fhss.scoring.exception.CustomerNotFoundException;
import com.idbi.fhss.scoring.repository.CustomerProfileRepository;
import com.idbi.fhss.scoring.repository.UnderwriterDecisionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DecisionService {

    private static final Logger log = LoggerFactory.getLogger(DecisionService.class);

    private final UnderwriterDecisionRepository decisionRepo;
    private final CustomerProfileRepository profileRepo;

    @org.springframework.beans.factory.annotation.Value("${app.decision.default-reviewer:underwriter}")
    private String defaultReviewer;

    public DecisionService(UnderwriterDecisionRepository decisionRepo, CustomerProfileRepository profileRepo) {
        this.decisionRepo = decisionRepo;
        this.profileRepo = profileRepo;
    }

    public DecisionResponse submitDecision(DecisionRequest request) {
        if (!profileRepo.findByCustomerId(request.customerId()).isPresent()) {
            throw new CustomerNotFoundException(request.customerId());
        }

        var entity = new UnderwriterDecision();
        entity.setCustomerId(request.customerId());
        entity.setDecision(request.decision().toUpperCase());
        entity.setRemarks(request.remarks());
        entity.setReviewer(defaultReviewer);
        var saved = decisionRepo.save(entity);

        log.info("Decision recorded for {}: {}", request.customerId(), request.decision());
        return toResponse(saved);
    }

    public List<DecisionResponse> getDecisions(String customerId) {
        return decisionRepo.findByCustomerIdOrderByCreatedAtDesc(customerId).stream()
                .map(this::toResponse)
                .toList();
    }

    public List<DecisionResponse> getPendingReviews() {
        return decisionRepo.findByDecisionOrderByCreatedAtDesc("REVIEW").stream()
                .map(this::toResponse)
                .toList();
    }

    private DecisionResponse toResponse(UnderwriterDecision d) {
        return new DecisionResponse(
                d.getId(), d.getCustomerId(), d.getDecision(),
                d.getRemarks(), d.getReviewer(), d.getCreatedAt());
    }
}
