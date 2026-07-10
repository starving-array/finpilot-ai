package com.idbi.fhss.scoring;

import com.idbi.fhss.scoring.entity.AuditLogV2;
import com.idbi.fhss.scoring.repository.AuditLogV2Repository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class AuditLogV2RepositoryTest {

    @Autowired private AuditLogV2Repository repository;

    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }

    @Test
    void shouldSaveAndFindByCustomerId() {
        var audit = createAudit("CUST00001", "disciplined", 0.85);
        repository.save(audit);

        var results = repository.findByCustomerIdOrderByScoredAtDesc("CUST00001");

        assertEquals(1, results.size());
        assertEquals("disciplined", results.get(0).getBucket());
    }

    @Test
    void shouldReturnEntriesInDescendingOrder() {
        var older = createAudit("CUST00001", "disciplined", 0.85);
        older.setScoredAt(Instant.now().minusSeconds(3600));
        var newer = createAudit("CUST00001", "non-disciplined", 0.65);
        newer.setScoredAt(Instant.now());

        repository.save(older);
        repository.save(newer);

        var results = repository.findByCustomerIdOrderByScoredAtDesc("CUST00001");

        assertEquals(2, results.size());
        assertTrue(results.get(0).getScoredAt().isAfter(results.get(1).getScoredAt()));
    }

    @Test
    void shouldReturnEmptyForUnknownCustomer() {
        var results = repository.findByCustomerIdOrderByScoredAtDesc("UNKNOWN");

        assertTrue(results.isEmpty());
    }

    @Test
    void shouldStoreAllFields() {
        var audit = new AuditLogV2();
        audit.setCustomerId("CUST00042");
        audit.setBucket("yes-to-go");
        audit.setConfidence(BigDecimal.valueOf(0.78));
        audit.setBlankSlateFlag(false);
        audit.setModelVersion("2.0.0");
        audit.setShapReasons("{\"payment_regularity\": 0.3}");
        audit.setCapacityFlag("{\"flag\":\"normal\"}");
        audit.setEpfoFlag("{\"flag\":\"plausible\",\"implied_wage\":15000}");
        audit.setSeasonalityFlags("{\"fuel\":{\"flag\":\"normal\"}}");
        audit.setSource("live");
        audit.setScoredAt(Instant.now());

        repository.save(audit);

        var results = repository.findByCustomerIdOrderByScoredAtDesc("CUST00042");
        assertEquals(1, results.size());
        var saved = results.get(0);
        assertEquals("yes-to-go", saved.getBucket());
        assertEquals("live", saved.getSource());
        assertEquals("2.0.0", saved.getModelVersion());
        assertFalse(saved.isBlankSlateFlag());
    }

    @Test
    void shouldHandleMultipleEntriesForSameCustomer() {
        for (int i = 0; i < 5; i++) {
            var audit = createAudit("CUST00099", "disciplined", 0.8 + i * 0.02);
            audit.setScoredAt(Instant.now().minusSeconds(i * 60));
            repository.save(audit);
        }

        var results = repository.findByCustomerIdOrderByScoredAtDesc("CUST00099");

        assertEquals(5, results.size());
    }

    @Test
    void shouldStoreBlankSlateFlag() {
        var audit = createAudit("CUST-BLANK", "no-to-go", 0.3);
        audit.setBlankSlateFlag(true);
        repository.save(audit);

        var results = repository.findByCustomerIdOrderByScoredAtDesc("CUST-BLANK");
        assertTrue(results.get(0).isBlankSlateFlag());
    }

    private AuditLogV2 createAudit(String customerId, String bucket, double confidence) {
        var audit = new AuditLogV2();
        audit.setCustomerId(customerId);
        audit.setBucket(bucket);
        audit.setConfidence(BigDecimal.valueOf(confidence));
        audit.setBlankSlateFlag(false);
        audit.setModelVersion("2.0.0");
        audit.setShapReasons("{}");
        audit.setCapacityFlag("{}");
        audit.setEpfoFlag("{}");
        audit.setSeasonalityFlags("{}");
        audit.setSource("live");
        audit.setScoredAt(Instant.now());
        return audit;
    }
}
