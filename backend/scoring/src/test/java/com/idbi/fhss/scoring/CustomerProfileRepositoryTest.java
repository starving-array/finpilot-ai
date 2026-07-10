package com.idbi.fhss.scoring;

import com.idbi.fhss.scoring.entity.CustomerProfile;
import com.idbi.fhss.scoring.repository.CustomerProfileRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class CustomerProfileRepositoryTest {

    @Autowired private CustomerProfileRepository repository;

    @Test
    void shouldSaveAndFindByCustomerId() {
        var profile = createProfile("CUST-TST-001");
        repository.save(profile);

        var found = repository.findByCustomerId("CUST-TST-001");

        assertTrue(found.isPresent());
        assertEquals("Test Business", found.get().getBusinessName());
        assertEquals("retail", found.get().getBusinessType());
    }

    @Test
    void shouldReturnEmptyForUnknownCustomer() {
        var found = repository.findByCustomerId("DOES-NOT-EXIST");

        assertTrue(found.isEmpty());
    }

    @Test
    void shouldSaveWithAllFields() {
        var profile = createProfile("CUST-TST-002");
        profile.setGstRegistered(true);
        profile.setGstMonthlyTurnoverAvg(BigDecimal.valueOf(500000));
        profile.setGstFilingRegularity(BigDecimal.valueOf(0.95));
        profile.setUpiMonthlyTxnCount(100);
        profile.setUpiMonthlyTxnValue(BigDecimal.valueOf(200000));
        profile.setElectricityMonthlyUnitsAvg(BigDecimal.valueOf(1500));
        profile.setElectricityPaymentDelayDaysAvg(BigDecimal.valueOf(5));
        profile.setEpfoContributionRegularity(BigDecimal.valueOf(0.85));
        profile.setEpfoEmployeeCount(20);
        profile.setEpfoContributionAmount(BigDecimal.valueOf(40000));
        profile.setWaterMonthlyConsumptionKl(BigDecimal.valueOf(120));
        profile.setWaterPaymentDelayDaysAvg(BigDecimal.valueOf(2));
        profile.setFuelMonthlySpendAvg(BigDecimal.valueOf(60000));
        profile.setFuelSpendVolatility(BigDecimal.valueOf(0.25));
        profile.setYearsInOperation(BigDecimal.valueOf(10));
        profile.setRequestedLoanAmount(BigDecimal.valueOf(1000000));
        profile.setBlankSlate(false);
        repository.save(profile);

        var found = repository.findByCustomerId("CUST-TST-002");
        assertTrue(found.isPresent());
        assertEquals(0.95, found.get().getGstFilingRegularity().doubleValue(), 0.001);
        assertEquals(100, found.get().getUpiMonthlyTxnCount());
        assertEquals(10, found.get().getYearsInOperation().doubleValue(), 0.001);
        assertFalse(found.get().isBlankSlate());
    }

    @Test
    void shouldDetectBlankSlateFlag() {
        var profile = createProfile("CUST-BLANK-001");
        profile.setBlankSlate(true);
        repository.save(profile);

        var found = repository.findByCustomerId("CUST-BLANK-001");
        assertTrue(found.get().isBlankSlate());
    }

    @Test
    void shouldUpdateExistingProfile() {
        var profile = createProfile("CUST-UPD-001");
        repository.save(profile);

        profile.setBusinessName("Updated Business");
        profile.setRequestedLoanAmount(BigDecimal.valueOf(750000));
        repository.save(profile);

        var found = repository.findByCustomerId("CUST-UPD-001");
        assertTrue(found.isPresent());
        assertEquals("Updated Business", found.get().getBusinessName());
        assertEquals(750000, found.get().getRequestedLoanAmount().doubleValue(), 0.01);
    }

    private CustomerProfile createProfile(String customerId) {
        var profile = new CustomerProfile();
        profile.setCustomerId(customerId);
        profile.setBusinessName("Test Business");
        profile.setOwnerName("Test Owner");
        profile.setBusinessType("retail");
        profile.setState("Maharashtra");
        profile.setGstRegistered(true);
        profile.setBlankSlate(false);
        profile.setCreatedAt(Instant.now());
        return profile;
    }
}
