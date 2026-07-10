package com.idbi.fhss.scoring;

import com.idbi.fhss.scoring.dto.DecisionRequest;
import com.idbi.fhss.scoring.entity.CustomerProfile;
import com.idbi.fhss.scoring.entity.UnderwriterDecision;
import com.idbi.fhss.scoring.exception.CustomerNotFoundException;
import com.idbi.fhss.scoring.repository.CustomerProfileRepository;
import com.idbi.fhss.scoring.repository.UnderwriterDecisionRepository;
import com.idbi.fhss.scoring.service.DecisionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DecisionServiceTest {

    @Mock private UnderwriterDecisionRepository decisionRepo;
    @Mock private CustomerProfileRepository profileRepo;
    @Captor private ArgumentCaptor<UnderwriterDecision> decisionCaptor;

    private DecisionService service;

    @BeforeEach
    void setUp() {
        service = new DecisionService(decisionRepo, profileRepo);
    }

    @Test
    void submitDecision_shouldSaveAndReturnResponse() {
        when(profileRepo.findByCustomerId("CUST00001")).thenReturn(Optional.of(new CustomerProfile()));
        when(decisionRepo.save(any())).thenAnswer(invocation -> {
            var entity = invocation.<UnderwriterDecision>getArgument(0);
            entity.setId(1L);
            entity.setCreatedAt(Instant.now());
            return entity;
        });

        var request = new DecisionRequest("CUST00001", "APPROVE", "Good profile");
        var response = service.submitDecision(request);

        assertEquals("CUST00001", response.customerId());
        assertEquals("APPROVE", response.decision());
        assertEquals("Good profile", response.remarks());

        verify(decisionRepo).save(decisionCaptor.capture());
        var saved = decisionCaptor.getValue();
        assertEquals("CUST00001", saved.getCustomerId());
        assertEquals("APPROVE", saved.getDecision());
        assertEquals("test-underwriter", saved.getReviewer());
    }

    @Test
    void submitDecision_shouldThrowWhenCustomerNotFound() {
        when(profileRepo.findByCustomerId("UNKNOWN")).thenReturn(Optional.empty());

        var request = new DecisionRequest("UNKNOWN", "REVIEW", "Need more info");

        assertThrows(CustomerNotFoundException.class,
                () -> service.submitDecision(request));
        verify(decisionRepo, never()).save(any());
    }

    @Test
    void submitDecision_shouldUppercaseDecision() {
        when(profileRepo.findByCustomerId("CUST00001")).thenReturn(Optional.of(new CustomerProfile()));
        when(decisionRepo.save(any())).thenAnswer(invocation -> {
            var entity = invocation.<UnderwriterDecision>getArgument(0);
            entity.setId(2L);
            entity.setCreatedAt(Instant.now());
            return entity;
        });

        var request = new DecisionRequest("CUST00001", "reject", "Not suitable");
        var response = service.submitDecision(request);

        assertEquals("REJECT", response.decision());
    }

    @Test
    void getDecisions_shouldReturnListForCustomer() {
        var decisions = List.of(
                createDecision(1L, "CUST00001", "APPROVE"),
                createDecision(2L, "CUST00001", "REVIEW"));
        when(decisionRepo.findByCustomerIdOrderByCreatedAtDesc("CUST00001"))
                .thenReturn(decisions);

        var result = service.getDecisions("CUST00001");

        assertEquals(2, result.size());
        assertEquals("APPROVE", result.get(0).decision());
        assertEquals("REVIEW", result.get(1).decision());
    }

    @Test
    void getDecisions_shouldReturnEmptyForUnknown() {
        when(decisionRepo.findByCustomerIdOrderByCreatedAtDesc("UNKNOWN"))
                .thenReturn(List.of());

        var result = service.getDecisions("UNKNOWN");

        assertTrue(result.isEmpty());
    }

    @Test
    void getPendingReviews_shouldReturnOnlyReviewDecisions() {
        var reviews = List.of(
                createDecision(3L, "CUST00042", "REVIEW"),
                createDecision(4L, "CUST00087", "REVIEW"));
        when(decisionRepo.findByDecisionOrderByCreatedAtDesc("REVIEW"))
                .thenReturn(reviews);

        var result = service.getPendingReviews();

        assertEquals(2, result.size());
        assertTrue(result.stream().allMatch(d -> d.decision().equals("REVIEW")));
    }

    @Test
    void getPendingReviews_shouldReturnEmptyWhenNone() {
        when(decisionRepo.findByDecisionOrderByCreatedAtDesc("REVIEW"))
                .thenReturn(List.of());

        var result = service.getPendingReviews();

        assertTrue(result.isEmpty());
    }

    private UnderwriterDecision createDecision(Long id, String customerId, String decision) {
        var d = new UnderwriterDecision();
        d.setId(id);
        d.setCustomerId(customerId);
        d.setDecision(decision);
        d.setRemarks("Test remarks");
        d.setReviewer("underwriter");
        d.setCreatedAt(Instant.now());
        return d;
    }
}
