package com.idbi.fhss.feature.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.common.dto.FeatureVectorDTO;
import com.idbi.fhss.feature.entity.FeatureSnapshot;
import com.idbi.fhss.feature.repository.FeatureSnapshotRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class FeatureService {

    private static final String SCHEMA_VERSION = "1.0";
    private static final String COMPUTATION_VERSION = "1.0.0";

    static final List<String> FEATURE_NAMES = List.of(
        "gst_filing_regularity", "gst_tax_growth_yoy", "gst_compliance_score",
        "upi_txn_volume_30d", "upi_merchant_diversity", "upi_inflow_outflow_ratio",
        "bureau_score", "bureau_enquiry_velocity", "bureau_credit_utilization",
        "electricity_avg_consumption", "electricity_payment_regularity",
        "water_consumption_stability", "water_payment_regularity",
        "epfo_contribution_regularity", "epfo_employee_trend",
        "fuel_expense_regularity", "fuel_liters_cv"
    );

    private static final Logger log = LoggerFactory.getLogger(FeatureService.class);

    private static final double MISSING_SENTINEL = -999.0;

    private final FeatureSnapshotRepository featureSnapshotRepository;
    private final ObjectMapper objectMapper;

    public FeatureService(FeatureSnapshotRepository featureSnapshotRepository,
                          ObjectMapper objectMapper) {
        this.featureSnapshotRepository = featureSnapshotRepository;
        this.objectMapper = objectMapper;
    }

    public FeatureVectorDTO computeFeatures(UUID customerId,
                                            String traditionalData,
                                            String alternativeData) {
        log.info("Computing features for customerId={}", customerId);
        var rawValues = extractRawFeatureValues(traditionalData, alternativeData);
        var features = new LinkedHashMap<String, Double>();
        var missingFlags = new LinkedHashMap<String, Double>();
        var validationWarnings = new ArrayList<String>();
        int presentCount = 0;

        for (var name : FEATURE_NAMES) {
            var val = rawValues.getOrDefault(name, MISSING_SENTINEL);
            if (val == null || val == MISSING_SENTINEL) {
                features.put(name, 0.0);
                missingFlags.put(name + "_missing", 1.0);
                log.debug("Feature {} is MISSING for customerId={}", name, customerId);
            } else {
                features.put(name, val);
                missingFlags.put(name + "_missing", 0.0);
                presentCount++;
                log.debug("Feature {} = {} for customerId={}", name, val, customerId);
            }
        }

        features.putAll(missingFlags);

        double completeness = (double) presentCount / FEATURE_NAMES.size();
        boolean blankSlate = completeness < 0.15;

        if (blankSlate) {
            validationWarnings.add("Insufficient alternative data, operating in blank-slate mode");
            log.warn("Customer {} in blank-slate mode: {}/{} features present", customerId, presentCount, FEATURE_NAMES.size());
        }
        if (presentCount == 0) {
            validationWarnings.add("No features could be extracted from available data");
        }

        log.info("Feature computation complete for customerId={}: {}/{} features present, completeness={}, blankSlate={}",
            customerId, presentCount, FEATURE_NAMES.size(), String.format("%.2f", completeness), blankSlate);

        return new FeatureVectorDTO(
            customerId,
            features,
            completeness,
            blankSlate,
            validationWarnings,
            SCHEMA_VERSION,
            COMPUTATION_VERSION
        );
    }

    @Transactional
    public FeatureSnapshot persistSnapshot(UUID customerId, FeatureVectorDTO featureVector) {
        var snapshot = new FeatureSnapshot();
        snapshot.setCustomerId(customerId);
        try {
            snapshot.setFeatureVector(objectMapper.writeValueAsString(featureVector.features()));
        } catch (Exception e) {
            throw new RuntimeException("Failed to serialize feature vector", e);
        }
        snapshot.setSchemaVersion(featureVector.schemaVersion());
        snapshot.setComputationVersion(featureVector.computationVersion());
        snapshot.setCompletenessScore(featureVector.completenessScore());
        snapshot.setBlankSlateMode(featureVector.blankSlateMode());
        return featureSnapshotRepository.save(snapshot);
    }

    public Map<String, Double> extractRawFeatureValues(String traditionalData,
                                                        String alternativeData) {
        var result = new LinkedHashMap<String, Double>();
        var traditional = parseJsonObject(traditionalData);
        var alternative = parseJsonObject(alternativeData);

        result.put("gst_filing_regularity", getNestedDouble(traditional, "gst", "filing_regularity"));
        result.put("gst_tax_growth_yoy", getNestedDouble(traditional, "gst", "tax_growth_yoy"));
        result.put("gst_compliance_score", getNestedDouble(traditional, "gst", "compliance_score"));
        result.put("upi_txn_volume_30d", getNestedDouble(traditional, "upi", "txn_volume_30d"));
        result.put("upi_merchant_diversity", getNestedDouble(traditional, "upi", "merchant_diversity"));
        result.put("upi_inflow_outflow_ratio", getNestedDouble(traditional, "upi", "inflow_outflow_ratio"));
        result.put("bureau_score", getNestedDouble(traditional, "bureau", "bureau_score"));
        result.put("bureau_enquiry_velocity", getNestedDouble(traditional, "bureau", "enquiry_count_90d"));
        result.put("bureau_credit_utilization", getNestedDouble(traditional, "bureau", "credit_utilization"));
        result.put("electricity_avg_consumption", getNestedDouble(alternative, "electricity", "avg_monthly_consumption"));
        result.put("electricity_payment_regularity", getNestedDouble(alternative, "electricity", "payment_regularity"));
        result.put("water_consumption_stability", getNestedDouble(alternative, "water", "consumption_stability"));
        result.put("water_payment_regularity", getNestedDouble(alternative, "water", "payment_regularity"));
        result.put("epfo_contribution_regularity", getNestedDouble(alternative, "epfo", "contribution_regularity"));
        result.put("epfo_employee_trend", getNestedDouble(alternative, "epfo", "employee_count_trend_6m"));
        result.put("fuel_expense_regularity", getNestedDouble(alternative, "fuel", "expense_regularity"));
        result.put("fuel_liters_cv", getNestedDouble(alternative, "fuel", "liters_per_month_cv"));

        return result;
    }

    private Map<String, Object> parseJsonObject(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    private Double getNestedDouble(Map<String, Object> root, String... path) {
        if (root == null || path.length == 0) return MISSING_SENTINEL;
        Map<String, Object> current = root;
        for (int i = 0; i < path.length - 1; i++) {
            var next = current.get(path[i]);
            if (next instanceof Map<?, ?> nextMap) {
                current = (Map<String, Object>) nextMap;
            } else {
                return MISSING_SENTINEL;
            }
        }
        var val = current.get(path[path.length - 1]);
        if (val == null) return MISSING_SENTINEL;
        if (val instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(val.toString());
        } catch (NumberFormatException e) {
            return MISSING_SENTINEL;
        }
    }
}
