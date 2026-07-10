package com.idbi.fhss.audit;

import com.idbi.fhss.audit.entity.AuditLog;
import com.idbi.fhss.audit.repository.AuditLogRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.time.Instant;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
class AuditLogRepositoryTest {

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Test
    void shouldSaveAndFindAuditLog() {
        var log = new AuditLog();
        log.setRequestId(UUID.randomUUID());
        log.setCustomerId(UUID.randomUUID());
        log.setActor("underwriter1");
        log.setAction("SCORING_COMPLETED");
        log.setInputHash("abc123");
        log.setOutputHash("def456");

        var saved = auditLogRepository.save(log);
        assertNotNull(saved.getLogId());
        assertNotNull(saved.getTimestamp());

        var found = auditLogRepository.findByCustomerIdOrderByTimestampDesc(log.getCustomerId());
        assertEquals(1, found.size());
        assertEquals("underwriter1", found.get(0).getActor());
    }

    @Test
    void shouldStoreDecision() {
        var log = new AuditLog();
        log.setRequestId(UUID.randomUUID());
        log.setCustomerId(UUID.randomUUID());
        log.setActor("underwriter2");
        log.setAction("UNDERWRITER_DECISION");
        log.setDecision("APPROVE");
        log.setNotes("All criteria met");
        auditLogRepository.save(log);

        var found = auditLogRepository.findByCustomerIdOrderByTimestampDesc(log.getCustomerId());
        assertEquals(1, found.size());
        assertEquals("APPROVE", found.get(0).getDecision());
        assertEquals("All criteria met", found.get(0).getNotes());
    }

    @Test
    void shouldFilterByAction() {
        var customerId = UUID.randomUUID();
        var log1 = new AuditLog();
        log1.setRequestId(UUID.randomUUID());
        log1.setCustomerId(customerId);
        log1.setActor("system");
        log1.setAction("SCORING_COMPLETED");
        auditLogRepository.save(log1);

        var log2 = new AuditLog();
        log2.setRequestId(UUID.randomUUID());
        log2.setCustomerId(customerId);
        log2.setActor("underwriter");
        log2.setAction("UNDERWRITER_DECISION");
        log2.setDecision("REJECT");
        auditLogRepository.save(log2);

        var scoringLogs = auditLogRepository
                .findByCustomerIdAndActionOrderByTimestampDesc(customerId, "SCORING_COMPLETED");
        assertEquals(1, scoringLogs.size());
    }

    @Test
    void shouldQueryByActionAndTimeRange() {
        var log = new AuditLog();
        log.setRequestId(UUID.randomUUID());
        log.setActor("system");
        log.setAction("MODEL_DEPLOYED");
        log.setTimestamp(Instant.now());
        auditLogRepository.save(log);

        var results = auditLogRepository
                .findByActionAndTimestampBetween("MODEL_DEPLOYED",
                        Instant.now().minusSeconds(3600), Instant.now().plusSeconds(3600));
        assertFalse(results.isEmpty());
    }

    @Test
    void shouldAllowMultipleEntries() {
        var customerId = UUID.randomUUID();
        for (int i = 0; i < 5; i++) {
            var log = new AuditLog();
            log.setRequestId(UUID.randomUUID());
            log.setCustomerId(customerId);
            log.setActor("system");
            log.setAction("CUSTOMER_UPDATED");
            auditLogRepository.save(log);
        }

        var logs = auditLogRepository.findByCustomerIdOrderByTimestampDesc(customerId);
        assertEquals(5, logs.size());
    }

    @Test
    void shouldHandleNoResults() {
        var logs = auditLogRepository.findByCustomerIdOrderByTimestampDesc(UUID.randomUUID());
        assertTrue(logs.isEmpty());
    }

    @Test
    void shouldStoreMetadataAsJsonb() {
        var log = new AuditLog();
        log.setRequestId(UUID.randomUUID());
        log.setActor("system");
        log.setAction("CONFIG_CHANGED");
        log.setMetadata("{\"changed_fields\": [\"threshold\"], \"previous_value\": 0.3, \"new_value\": 0.4}");
        auditLogRepository.save(log);

        var found = auditLogRepository.findById(log.getLogId());
        assertTrue(found.isPresent());
        assertTrue(found.get().getMetadata().contains("threshold"));
    }
}
