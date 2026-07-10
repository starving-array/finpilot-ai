package com.idbi.fhss.feature;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.feature.service.FeatureService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
class FeatureServiceTest {

    @Autowired
    private FeatureService featureService;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void shouldComputeFeaturesFromCompleteData() {
        var traditional = "{\"gst\":{\"filing_regularity\":0.95,\"tax_growth_yoy\":0.12,\"compliance_score\":0.88},\"upi\":{\"txn_volume_30d\":450.0,\"merchant_diversity\":12.0,\"inflow_outflow_ratio\":1.5},\"bureau\":{\"bureau_score\":720.0,\"enquiry_count_90d\":2.0,\"credit_utilization\":0.35}}";
        var alternative = "{\"electricity\":{\"avg_monthly_consumption\":2500.0,\"payment_regularity\":0.92},\"water\":{\"consumption_stability\":0.85,\"payment_regularity\":0.88},\"epfo\":{\"contribution_regularity\":0.78,\"employee_count_trend_6m\":0.05},\"fuel\":{\"expense_regularity\":0.82,\"liters_per_month_cv\":1200.0}}";

        var result = featureService.computeFeatures(UUID.randomUUID(), traditional, alternative);

        assertEquals(34, result.features().size());
        assertFalse(result.blankSlateMode());
        assertTrue(result.completenessScore() > 0.99);
        assertTrue(result.validationWarnings().isEmpty());
    }

    @Test
    void shouldDetectBlankSlate() {
        var result = featureService.computeFeatures(UUID.randomUUID(), "{}", "{}");

        assertEquals(34, result.features().size());
        assertTrue(result.blankSlateMode());
        assertTrue(result.completenessScore() < 0.15);
        assertFalse(result.validationWarnings().isEmpty());
    }

    @Test
    void shouldHandleNullData() {
        var result = featureService.computeFeatures(UUID.randomUUID(), null, null);

        assertEquals(34, result.features().size());
        assertTrue(result.blankSlateMode());
    }

    @Test
    void shouldHandlePartialData() {
        var traditional = "{\"gst\":{\"filing_regularity\":0.9},\"bureau\":{\"bureau_score\":700.0}}";
        var alternative = "{\"electricity\":{\"avg_monthly_consumption\":1000.0}}";

        var result = featureService.computeFeatures(UUID.randomUUID(), traditional, alternative);

        var presentCount = result.features().entrySet().stream()
            .filter(e -> !e.getKey().endsWith("_missing"))
            .filter(e -> e.getValue() != 0.0)
            .count();
        assertTrue(presentCount >= 3);
        assertFalse(result.blankSlateMode());
    }

    @Test
    void shouldSetMissingIndicators() {
        var result = featureService.computeFeatures(UUID.randomUUID(), "{}", "{}");

        for (var entry : result.features().entrySet()) {
            if (entry.getKey().endsWith("_missing")) {
                assertEquals(1.0, entry.getValue(), "Missing indicator should be 1 for " + entry.getKey());
            }
        }
    }

    @Test
    void shouldNotSetMissingIndicatorsForPresentFeatures() {
        var traditional = "{\"gst\":{\"filing_regularity\":0.9}}";
        var result = featureService.computeFeatures(UUID.randomUUID(), traditional, "{}");

        assertEquals(0.0, result.features().get("gst_filing_regularity_missing"));
        assertEquals(1.0, result.features().get("upi_txn_volume_30d_missing"));
    }
}
