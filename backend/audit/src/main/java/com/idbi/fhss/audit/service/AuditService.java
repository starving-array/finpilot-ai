package com.idbi.fhss.audit.service;

import com.idbi.fhss.audit.entity.AuditLog;
import com.idbi.fhss.audit.repository.AuditLogRepository;
import com.idbi.fhss.common.enums.AuditAction;
import com.idbi.fhss.common.enums.Decision;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);

    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;

    public AuditService(AuditLogRepository auditLogRepository, ObjectMapper objectMapper) {
        this.auditLogRepository = auditLogRepository;
        this.objectMapper = objectMapper;
    }

    public AuditLog log(UUID requestId, UUID customerId, String actor, AuditAction action,
                        Map<String, Object> inputData, Map<String, Object> outputData,
                        Decision decision, String notes) {
        var entry = new AuditLog();
        entry.setRequestId(requestId);
        entry.setCustomerId(customerId);
        entry.setTimestamp(Instant.now());
        entry.setActor(actor);
        entry.setAction(action.name());
        entry.setInputHash(hashData(inputData));
        entry.setOutputHash(hashData(outputData));
        entry.setDecision(decision != null ? decision.name() : null);
        entry.setNotes(notes);
        try {
            var metadata = Map.of(
                "action", action.name(),
                "timestamp", entry.getTimestamp().toString()
            );
            entry.setMetadata(objectMapper.writeValueAsString(metadata));
        } catch (Exception e) {
            entry.setMetadata("{}");
        }

        var saved = auditLogRepository.save(entry);
        log.info("Audit log created: requestId={}, action={}, actor={}", requestId, action, actor);
        return saved;
    }

    public AuditLog logScoring(UUID requestId, UUID customerId, String actor,
                               Map<String, Object> inputData,
                               Map<String, Object> outputData,
                               String decision) {
        Decision mappedDecision = null;
        try {
            if (decision != null) {
                mappedDecision = Decision.valueOf(decision);
            }
        } catch (IllegalArgumentException e) {
            mappedDecision = null;
        }
        return log(requestId, customerId, actor, AuditAction.SCORING_COMPLETED,
            inputData, outputData, mappedDecision, "Scoring completed");
    }

    private String hashData(Map<String, Object> data) {
        if (data == null || data.isEmpty()) {
            return null;
        }
        try {
            var json = objectMapper.writeValueAsString(data);
            var digest = MessageDigest.getInstance("SHA-256");
            var hash = digest.digest(json.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            log.warn("Failed to hash audit data: {}", e.getMessage());
            return null;
        }
    }
}
