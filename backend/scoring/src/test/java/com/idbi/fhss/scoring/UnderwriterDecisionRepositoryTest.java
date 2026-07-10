package com.idbi.fhss.scoring;

import com.idbi.fhss.scoring.entity.UnderwriterDecision;
import com.idbi.fhss.scoring.repository.UnderwriterDecisionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class UnderwriterDecisionRepositoryTest {

    @Autowired private UnderwriterDecisionRepository repository;

    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }

    @Test
    void shouldSaveAndFindByCustomerId() {
        var decision = createDecision("CUST00001", "APPROVE");
        repository.save(decision);

        var results = repository.findByCustomerIdOrderByCreatedAtDesc("CUST00001");

        assertEquals(1, results.size());
        assertEquals("APPROVE", results.get(0).getDecision());
    }

    @Test
    void shouldFindByDecisionType() {
        repository.save(createDecision("CUST00001", "REVIEW"));
        repository.save(createDecision("CUST00002", "REVIEW"));
        repository.save(createDecision("CUST00003", "APPROVE"));

        var reviews = repository.findByDecisionOrderByCreatedAtDesc("REVIEW");

        assertEquals(2, reviews.size());
        assertTrue(reviews.stream().allMatch(d -> d.getDecision().equals("REVIEW")));
    }

    @Test
    void shouldReturnMultipleDecisionsForSameCustomer() {
        repository.save(createDecision("CUST00001", "APPROVE"));
        repository.save(createDecision("CUST00001", "REVIEW"));

        var results = repository.findByCustomerIdOrderByCreatedAtDesc("CUST00001");

        assertEquals(2, results.size());
    }

    @Test
    void shouldReturnEmptyForUnknownCustomer() {
        var results = repository.findByCustomerIdOrderByCreatedAtDesc("UNKNOWN");

        assertTrue(results.isEmpty());
    }

    @Test
    void shouldReturnEmptyWhenNoPendingReviews() {
        repository.save(createDecision("CUST00001", "APPROVE"));
        repository.save(createDecision("CUST00002", "REJECT"));

        var reviews = repository.findByDecisionOrderByCreatedAtDesc("REVIEW");

        assertTrue(reviews.isEmpty());
    }

    @Test
    void shouldStoreRemarks() {
        var decision = createDecision("CUST00001", "REJECT");
        decision.setRemarks("Insufficient documentation");
        repository.save(decision);

        var results = repository.findByCustomerIdOrderByCreatedAtDesc("CUST00001");

        assertEquals("Insufficient documentation", results.get(0).getRemarks());
    }

    private UnderwriterDecision createDecision(String customerId, String decision) {
        var d = new UnderwriterDecision();
        d.setCustomerId(customerId);
        d.setDecision(decision);
        d.setRemarks("Test remarks");
        d.setReviewer("underwriter");
        return d;
    }
}
