package com.idbi.fhss.audit;

import com.idbi.fhss.audit.repository.AuditLogRepository;
import com.idbi.fhss.audit.service.AuditService;
import com.idbi.fhss.common.enums.AuditAction;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
class AuditServiceTest {

    @Autowired
    private AuditService auditService;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Test
    void shouldCreateAuditLog() {
        var logEntry = auditService.log(
            UUID.randomUUID(), UUID.randomUUID(), "test-user",
            AuditAction.SCORING_COMPLETED,
            Map.of("input", "data"),
            Map.of("output", "result"),
            null, "Test audit entry"
        );

        assertNotNull(logEntry.getLogId());
        assertEquals("SCORING_COMPLETED", logEntry.getAction());
        assertEquals("test-user", logEntry.getActor());
    }

    @Test
    void shouldCreateHashChain() {
        var customerId = UUID.randomUUID();

        var entry1 = auditService.log(
            UUID.randomUUID(), customerId, "user1",
            AuditAction.SCORING_REQUESTED,
            Map.of("req", "1"), Map.of("resp", "1"),
            null, "First entry"
        );
        assertNull(entry1.getPrevLogHash());

        var entry2 = auditService.log(
            UUID.randomUUID(), customerId, "user2",
            AuditAction.SCORING_COMPLETED,
            Map.of("req", "2"), Map.of("resp", "2"),
            null, "Second entry"
        );
        assertNotNull(entry2.getPrevLogHash());
        assertEquals(entry1.getOutputHash(), entry2.getPrevLogHash(),
            "prev_log_hash should match previous output_hash");
    }

    @Test
    void shouldLogScoringAction() {
        var logEntry = auditService.logScoring(
            UUID.randomUUID(), UUID.randomUUID(), "underwriter1",
            Map.of("customerId", "c1"), Map.of("category", "YES_TO_GO"),
            "APPROVE"
        );

        assertEquals("SCORING_COMPLETED", logEntry.getAction());
        assertEquals("APPROVE", logEntry.getDecision());
    }

    @Test
    void shouldHandleNullInput() {
        var logEntry = auditService.log(
            UUID.randomUUID(), UUID.randomUUID(), "system",
            AuditAction.CONFIG_CHANGED,
            null, null, null, "Null test"
        );

        assertNotNull(logEntry.getLogId());
        assertNull(logEntry.getInputHash());
        assertNull(logEntry.getOutputHash());
    }

    @Test
    void shouldPersistAndRetrieve() {
        var requestId = UUID.randomUUID();
        auditService.logScoring(
            requestId, UUID.randomUUID(), "auditor",
            Map.of("key", "value"), Map.of("result", "ok"), null
        );

        var allLogs = auditLogRepository.findAll();
        var found = allLogs.stream()
            .filter(l -> l.getRequestId().equals(requestId))
            .findFirst();
        assertTrue(found.isPresent());
        assertEquals("auditor", found.get().getActor());
    }
}
