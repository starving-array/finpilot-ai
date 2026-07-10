package com.idbi.fhss.feature;

import com.idbi.fhss.feature.entity.FeatureSnapshot;
import com.idbi.fhss.feature.repository.FeatureSnapshotRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
class FeatureSnapshotRepositoryTest {

    @Autowired
    private FeatureSnapshotRepository featureSnapshotRepository;

    @Test
    void shouldSaveAndFindSnapshot() {
        var snapshot = new FeatureSnapshot();
        snapshot.setCustomerId(UUID.randomUUID());
        snapshot.setFeatureVector("{\"gst_filing_regularity\": 0.95, \"upi_volume\": 150.0}");
        snapshot.setSchemaVersion("1.0");
        snapshot.setComputationVersion("1.0.0");
        snapshot.setCompletenessScore(0.85);
        snapshot.setBlankSlateMode(false);

        var saved = featureSnapshotRepository.save(snapshot);
        assertNotNull(saved.getSnapshotId());

        var found = featureSnapshotRepository.findById(saved.getSnapshotId());
        assertTrue(found.isPresent());
        assertEquals(0.85, found.get().getCompletenessScore());
    }

    @Test
    void shouldFindLatestByCustomer() {
        var customerId = UUID.randomUUID();
        for (int i = 0; i < 3; i++) {
            var s = new FeatureSnapshot();
            s.setCustomerId(customerId);
            s.setFeatureVector("{}");
            s.setSchemaVersion("1.0");
            s.setComputationVersion("1.0.0");
            s.setCompletenessScore(0.5 + i * 0.1);
            s.setBlankSlateMode(false);
            featureSnapshotRepository.save(s);
            Thread.sleep(10); // ensure different created_at
        }

        var latest = featureSnapshotRepository.findTopByCustomerIdOrderByCreatedAtDesc(customerId);
        assertTrue(latest.isPresent());
        assertTrue(latest.get().getCompletenessScore() >= 0.7);
    }

    @Test
    void shouldStoreBlankSlateFlag() {
        var snapshot = new FeatureSnapshot();
        snapshot.setCustomerId(UUID.randomUUID());
        snapshot.setFeatureVector("{}");
        snapshot.setSchemaVersion("1.0");
        snapshot.setComputationVersion("1.0.0");
        snapshot.setCompletenessScore(0.25);
        snapshot.setBlankSlateMode(true);

        var saved = featureSnapshotRepository.save(snapshot);
        assertTrue(saved.isBlankSlateMode());
    }

    @Test
    void shouldHandleNoSnapshots() {
        var result = featureSnapshotRepository.findTopByCustomerIdOrderByCreatedAtDesc(UUID.randomUUID());
        assertTrue(result.isEmpty());
    }

    @Test
    void shouldHandleLargeFeatureVector() {
        var sb = new StringBuilder("{");
        for (int i = 0; i < 50; i++) {
            if (i > 0) sb.append(",");
            sb.append("\"feature_").append(i).append("\": ").append(Math.random());
        }
        sb.append("}");

        var snapshot = new FeatureSnapshot();
        snapshot.setCustomerId(UUID.randomUUID());
        snapshot.setFeatureVector(sb.toString());
        snapshot.setSchemaVersion("2.0");
        snapshot.setComputationVersion("2.0.0");
        snapshot.setCompletenessScore(1.0);
        snapshot.setBlankSlateMode(false);

        var saved = featureSnapshotRepository.save(snapshot);
        assertNotNull(saved.getSnapshotId());
    }
}
