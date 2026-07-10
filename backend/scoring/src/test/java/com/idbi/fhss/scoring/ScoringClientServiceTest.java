package com.idbi.fhss.scoring;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.scoring.dto.ScoreResponse;
import com.idbi.fhss.scoring.entity.AuditLogV2;
import com.idbi.fhss.scoring.entity.CustomerProfile;
import com.idbi.fhss.scoring.exception.CustomerNotFoundException;
import com.idbi.fhss.scoring.exception.ScoringServiceUnavailableException;
import com.idbi.fhss.scoring.repository.AuditLogV2Repository;
import com.idbi.fhss.scoring.repository.CustomerProfileRepository;
import com.idbi.fhss.scoring.service.ScoringClientService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ScoringClientServiceTest {

    @Mock private CustomerProfileRepository profileRepo;
    @Mock private AuditLogV2Repository auditRepo;
    @Mock private StringRedisTemplate redisTemplate;
    @Mock private ValueOperations<String, String> valueOps;

    private ObjectMapper objectMapper;
    private ScoringClientService service;

    private static final String CUSTOMER_ID = "CUST00001";
    private static final String REDIS_KEY = "score:test:CUST00001";

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        service = new ScoringClientService(
                profileRepo, auditRepo,
                "http://localhost:18000",
                redisTemplate, objectMapper);
        ReflectionTestUtils.setField(service, "redisKeyPrefix", "score:test:");
        ReflectionTestUtils.setField(service, "cacheTtlMinutes", 5L);
    }

    @Test
    void getCustomerProfile_shouldReturnProfileWithCompleteness() {
        var profile = createFullProfile();
        when(profileRepo.findByCustomerId(CUSTOMER_ID)).thenReturn(Optional.of(profile));

        var result = service.getCustomerProfile(CUSTOMER_ID);

        assertEquals(CUSTOMER_ID, result.customerId());
        assertEquals("Test Business", result.businessName());
        assertEquals("retail", result.businessType());
        assertEquals(1.0, result.dataCompleteness(), 0.01);
        assertFalse(result.blankSlate());
    }

    @Test
    void getCustomerProfile_shouldThrowWhenNotFound() {
        when(profileRepo.findByCustomerId("UNKNOWN")).thenReturn(Optional.empty());

        assertThrows(CustomerNotFoundException.class,
                () -> service.getCustomerProfile("UNKNOWN"));
    }

    @Test
    void getCustomerProfile_shouldComputePartialCompleteness() {
        var profile = new CustomerProfile();
        profile.setCustomerId(CUSTOMER_ID);
        profile.setBusinessName("Test Business");
        profile.setBusinessType("retail");
        profile.setGstRegistered(true);
        profile.setGstMonthlyTurnoverAvg(BigDecimal.valueOf(50000));
        when(profileRepo.findByCustomerId(CUSTOMER_ID)).thenReturn(Optional.of(profile));

        var result = service.getCustomerProfile(CUSTOMER_ID);

        assertTrue(result.dataCompleteness() > 0.1);
        assertTrue(result.dataCompleteness() < 1.0);
    }

    @Test
    void fallbackAfterCircuitBreaker_shouldReturnCacheHit() throws Exception {
        var cached = createScoreResponse("disciplined", 0.85);
        var cachedJson = objectMapper.writeValueAsString(cached);
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(REDIS_KEY)).thenReturn(cachedJson);

        var result = service.fallbackAfterCircuitBreaker(CUSTOMER_ID, new RuntimeException("CB open"));

        assertNotNull(result);
        assertEquals("disciplined", result.bucket());
        assertEquals("cache-hit", result.source());
    }

    @Test
    void fallbackAfterCircuitBreaker_shouldThrowCustomerNotFoundException() {
        assertThrows(CustomerNotFoundException.class,
                () -> service.fallbackAfterCircuitBreaker("UNKNOWN",
                        new CustomerNotFoundException("UNKNOWN")));
    }

    @Test
    void fallbackAfterCircuitBreaker_shouldThrowWhenNoCacheAndNoAudit() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(REDIS_KEY)).thenReturn(null);
        when(auditRepo.findByCustomerIdOrderByScoredAtDesc(CUSTOMER_ID)).thenReturn(List.of());

        assertThrows(ScoringServiceUnavailableException.class,
                () -> service.fallbackAfterCircuitBreaker(CUSTOMER_ID,
                        new RuntimeException("ML down")));
    }

    @Test
    void fallbackAfterCircuitBreaker_shouldReturnStaleAuditWhenNoCache() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(REDIS_KEY)).thenReturn(null);

        var audit = createAuditLogV2("non-disciplined", 0.6, true);
        when(auditRepo.findByCustomerIdOrderByScoredAtDesc(CUSTOMER_ID))
                .thenReturn(List.of(audit));

        var result = service.fallbackAfterCircuitBreaker(CUSTOMER_ID,
                new RuntimeException("ML down"));

        assertNotNull(result);
        assertEquals("non-disciplined", result.bucket());
        assertEquals("cache-fallback", result.source());
    }

    @Test
    void fallbackAfterRetry_shouldReturnCacheHit() throws Exception {
        var cached = createScoreResponse("no-to-go", 0.3);
        var cachedJson = objectMapper.writeValueAsString(cached);
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(REDIS_KEY)).thenReturn(cachedJson);

        var result = service.fallbackAfterRetry(CUSTOMER_ID, new RuntimeException("timeout"));

        assertNotNull(result);
        assertEquals("no-to-go", result.bucket());
        assertEquals("cache-hit", result.source());
    }

    @Test
    void fallbackAfterRetry_shouldRethrowCustomerNotFoundException() {
        assertThrows(CustomerNotFoundException.class,
                () -> service.fallbackAfterRetry("UNKNOWN",
                        new CustomerNotFoundException("UNKNOWN")));
    }

    @Test
    void getAuditHistory_shouldReturnEmptyListOnError() {
        when(auditRepo.findByCustomerIdOrderByScoredAtDesc(CUSTOMER_ID))
                .thenThrow(new RuntimeException("DB error"));

        var result = service.getAuditHistory(CUSTOMER_ID);

        assertTrue(result.isEmpty());
    }

    @Test
    void getAuditHistory_shouldReturnEmptyForUnknownCustomer() {
        when(auditRepo.findByCustomerIdOrderByScoredAtDesc("UNKNOWN"))
                .thenReturn(List.of());

        var result = service.getAuditHistory("UNKNOWN");

        assertTrue(result.isEmpty());
    }

    @Test
    void getAuditHistory_shouldReturnMappedEntries() {
        var audit = createAuditLogV2("disciplined", 0.9, false);
        when(auditRepo.findByCustomerIdOrderByScoredAtDesc(CUSTOMER_ID))
                .thenReturn(List.of(audit));

        var result = service.getAuditHistory(CUSTOMER_ID);

        assertEquals(1, result.size());
        assertEquals("disciplined", result.get(0).bucket());
        assertEquals("cache-fallback", result.get(0).source());
    }

    @Test
    void getCachedResult_shouldReturnNullWhenRedisFails() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(anyString())).thenThrow(new RuntimeException("Redis down"));

        var result = service.fallbackAfterCircuitBreaker(CUSTOMER_ID,
                new RuntimeException("test"));

        assertThrows(ScoringServiceUnavailableException.class, () -> {
            throw new AssertionError("Should have thrown");
        });
    }

    @Test
    void fromAuditEntity_shouldHandleNullCapFlag() {
        var audit = createAuditLogV2("yes-to-go", 0.8, false);
        audit.setCapacityFlag(null);

        when(auditRepo.findByCustomerIdOrderByScoredAtDesc(CUSTOMER_ID))
                .thenReturn(List.of(audit));
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(valueOps.get(REDIS_KEY)).thenReturn(null);

        var result = service.fallbackAfterCircuitBreaker(CUSTOMER_ID,
                new RuntimeException("test"));

        assertNotNull(result);
        assertEquals("cache-fallback", result.source());
    }

    private CustomerProfile createFullProfile() {
        var profile = new CustomerProfile();
        profile.setCustomerId(CUSTOMER_ID);
        profile.setBusinessName("Test Business");
        profile.setOwnerName("Test Owner");
        profile.setBusinessType("retail");
        profile.setState("Maharashtra");
        profile.setGstRegistered(true);
        profile.setGstMonthlyTurnoverAvg(BigDecimal.valueOf(500000));
        profile.setGstFilingRegularity(BigDecimal.valueOf(0.95));
        profile.setUpiMonthlyTxnCount(120);
        profile.setUpiMonthlyTxnValue(BigDecimal.valueOf(250000));
        profile.setElectricityMonthlyUnitsAvg(BigDecimal.valueOf(2000));
        profile.setElectricityPaymentDelayDaysAvg(BigDecimal.valueOf(2));
        profile.setEpfoContributionRegularity(BigDecimal.valueOf(0.9));
        profile.setEpfoEmployeeCount(25);
        profile.setEpfoContributionAmount(BigDecimal.valueOf(45000));
        profile.setWaterMonthlyConsumptionKl(BigDecimal.valueOf(150));
        profile.setWaterPaymentDelayDaysAvg(BigDecimal.valueOf(3));
        profile.setFuelMonthlySpendAvg(BigDecimal.valueOf(80000));
        profile.setFuelSpendVolatility(BigDecimal.valueOf(0.3));
        profile.setYearsInOperation(BigDecimal.valueOf(8));
        profile.setRequestedLoanAmount(BigDecimal.valueOf(500000));
        profile.setBlankSlate(false);
        profile.setCreatedAt(Instant.now());
        return profile;
    }

    private ScoreResponse createScoreResponse(String bucket, double probability) {
        return new ScoreResponse(
                CUSTOMER_ID, bucket, probability, 0.75,
                java.util.Map.of("payment_regularity", 0.8),
                new ScoreResponse.Flags(false,
                        new ScoreResponse.EpfoPlausibilityFlag("plausible", "OK", 15000.0, 10),
                        new ScoreResponse.CapacityFlag("normal", "OK", 0.4, "gst"),
                        new ScoreResponse.SeasonalityFlags(
                                new ScoreResponse.SeasonalityFlag("normal", "OK", 0.2, null),
                                new ScoreResponse.SeasonalityFlag("normal", "OK", 0.1, null))),
                new ScoreResponse.ShapExplanation(
                        java.util.Map.of("payment_regularity", 0.3), 0.5,
                        List.of(new ScoreResponse.FeatureRank("payment_regularity", 0.8, 0.3, 1, "positive", "Good payment behavior", "standard")),
                        "Summary"),
                "2.0.0", "live", null, "req-001", Instant.now(),
                "Test Business", "Test Owner", "retail", "Maharashtra", 500000.0);
    }

    private AuditLogV2 createAuditLogV2(String bucket, double confidence, boolean blankSlate) {
        var audit = new AuditLogV2();
        audit.setCustomerId(CUSTOMER_ID);
        audit.setBucket(bucket);
        audit.setConfidence(BigDecimal.valueOf(confidence));
        audit.setBlankSlateFlag(blankSlate);
        audit.setModelVersion("2.0.0");
        audit.setShapReasons("{}");
        audit.setCapacityFlag("{\"flag\":\"normal\",\"message\":\"OK\"}");
        audit.setEpfoFlag("{\"flag\":\"plausible\",\"message\":\"OK\"}");
        audit.setSeasonalityFlags("{\"fuel\":{\"flag\":\"normal\",\"message\":\"OK\"},\"electricity\":{\"flag\":\"normal\",\"message\":\"OK\"}}");
        audit.setSource("live");
        audit.setScoredAt(Instant.now());
        return audit;
    }
}
