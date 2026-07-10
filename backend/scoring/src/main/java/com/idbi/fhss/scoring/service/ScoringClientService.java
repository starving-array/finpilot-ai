package com.idbi.fhss.scoring.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.scoring.dto.CustomerProfileResponse;
import com.idbi.fhss.scoring.dto.ScoreResponse;
import com.idbi.fhss.scoring.dto.ScoreResponse.*;
import com.idbi.fhss.scoring.entity.AuditLogV2;
import com.idbi.fhss.scoring.entity.CustomerProfile;
import com.idbi.fhss.scoring.exception.*;
import com.idbi.fhss.scoring.repository.AuditLogV2Repository;
import com.idbi.fhss.scoring.repository.CustomerProfileRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.TimeUnit;

import static java.net.http.HttpClient.Version.HTTP_1_1;

@Service
public class ScoringClientService {

    private static final Logger log = LoggerFactory.getLogger(ScoringClientService.class);

    @Value("${app.redis.key-prefix:score:}")
    private String redisKeyPrefix;

    @Value("${app.redis.cache-ttl-minutes:30}")
    private long cacheTtlMinutes;

    @Value("${app.ml-service.http-timeout-seconds:10}")
    private int mlHttpTimeoutSeconds;

    private final CustomerProfileRepository profileRepo;
    private final AuditLogV2Repository auditRepo;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final String mlServiceUrl;
    private final HttpClient httpClient;

    public ScoringClientService(
            CustomerProfileRepository profileRepo,
            AuditLogV2Repository auditRepo,
            @Value("${app.ml-service.url}") String mlServiceUrl,
            StringRedisTemplate redisTemplate,
            ObjectMapper objectMapper) {
        this.profileRepo = profileRepo;
        this.auditRepo = auditRepo;
        this.mlServiceUrl = mlServiceUrl;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().version(HTTP_1_1).build();
    }

    @Retry(name = "scoringService", fallbackMethod = "fallbackAfterRetry")
    @CircuitBreaker(name = "scoringService", fallbackMethod = "fallbackAfterCircuitBreaker")
    public ScoreResponse score(String customerId) {
        log.info("Scoring customer: {}", customerId);

        var profile = profileRepo.findByCustomerId(customerId)
                .orElseThrow(() -> new CustomerNotFoundException(
                    "Customer profile not found: " + customerId));

        var predictRequest = buildPredictRequest(profile);
        String requestBody;
        try {
            requestBody = objectMapper.writeValueAsString(predictRequest);
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize predict request for " + customerId, e);
        }

        var start = System.currentTimeMillis();
        HttpResponse<String> response;
        try {
            var request = HttpRequest.newBuilder()
                    .uri(URI.create(mlServiceUrl + "/predict"))
                    .header("Content-Type", "application/json")
                    .timeout(java.time.Duration.ofSeconds(mlHttpTimeoutSeconds))
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (java.net.http.HttpConnectTimeoutException e) {
            throw new ScoringServiceTimeoutException("ML service timed out for " + customerId);
        } catch (java.io.IOException | InterruptedException e) {
            throw new ScoringServiceUnavailableException(
                "ML service unavailable for " + customerId + ": " + e.getMessage());
        }
        var elapsed = System.currentTimeMillis() - start;

        if (response.statusCode() == 503) {
            throw new ScoringServiceUnavailableException("ML service returned 503 for " + customerId);
        }
        if (response.statusCode() != 200) {
            throw new ScoringServiceUnavailableException(
                "ML service returned " + response.statusCode() + " for " + customerId);
        }

        var mlResult = parseMlResponse(response.body(), customerId);

        var loanAmount = profile.getRequestedLoanAmount() != null
                ? profile.getRequestedLoanAmount().doubleValue() : null;

        var result = new ScoreResponse(
                customerId, mlResult.bucket(), mlResult.probability(),
                mlResult.compositeScore(), mlResult.features(), mlResult.flags(),
                mlResult.shapExplanation(), mlResult.modelVersion(),
                "live", null, UUID.randomUUID().toString().substring(0, 8), Instant.now(),
                profile.getBusinessName(), profile.getOwnerName(),
                profile.getBusinessType(), profile.getState(), loanAmount
        );

        persistAudit(result, mlResult);
        cacheResult(result);
        log.info("Scored {} -> {} ({}%) in {}ms", customerId, result.bucket(),
                String.format("%.1f", result.probability() * 100), elapsed);

        return result;
    }

    public CustomerProfileResponse getCustomerProfile(String customerId) {
        var profile = profileRepo.findByCustomerId(customerId)
                .orElseThrow(() -> new CustomerNotFoundException(
                    "Customer profile not found: " + customerId));

        var nonNullFields = 0;
        var totalFields = 16;
        if (profile.getGstMonthlyTurnoverAvg() != null) nonNullFields++;
        if (profile.getGstFilingRegularity() != null) nonNullFields++;
        if (profile.getUpiMonthlyTxnCount() != null) nonNullFields++;
        if (profile.getUpiMonthlyTxnValue() != null) nonNullFields++;
        if (profile.getElectricityMonthlyUnitsAvg() != null) nonNullFields++;
        if (profile.getElectricityPaymentDelayDaysAvg() != null) nonNullFields++;
        if (profile.getEpfoContributionRegularity() != null) nonNullFields++;
        if (profile.getEpfoEmployeeCount() != null) nonNullFields++;
        if (profile.getEpfoContributionAmount() != null) nonNullFields++;
        if (profile.getWaterMonthlyConsumptionKl() != null) nonNullFields++;
        if (profile.getWaterPaymentDelayDaysAvg() != null) nonNullFields++;
        if (profile.getFuelMonthlySpendAvg() != null) nonNullFields++;
        if (profile.getFuelSpendVolatility() != null) nonNullFields++;
        if (profile.getYearsInOperation() != null) nonNullFields++;
        if (profile.getRequestedLoanAmount() != null) nonNullFields++;
        if (profile.isGstRegistered()) nonNullFields++;
        var completeness = Math.min(1.0, (double) nonNullFields / totalFields);

        return new CustomerProfileResponse(
                profile.getCustomerId(), profile.getBusinessName(),
                profile.getOwnerName(), profile.getBusinessType(),
                profile.getState(),
                profile.getYearsInOperation() != null ? profile.getYearsInOperation().doubleValue() : null,
                profile.getRequestedLoanAmount() != null ? profile.getRequestedLoanAmount().doubleValue() : null,
                profile.isBlankSlate(), completeness);
    }

    public ScoreResponse fallbackAfterCircuitBreaker(String customerId, Throwable t) {
        log.warn("Circuit breaker triggered for {}: {}", customerId,
                t != null ? t.getMessage() : "unknown");

        if (t instanceof CustomerNotFoundException) {
            throw (CustomerNotFoundException) t;
        }
        return tryCacheFallback(customerId);
    }

    public ScoreResponse fallbackAfterRetry(String customerId, Throwable t) {
        log.warn("Retries exhausted for {}: {}", customerId,
                t != null ? t.getMessage() : "unknown");

        if (t instanceof CustomerNotFoundException) {
            throw (CustomerNotFoundException) t;
        }
        return tryCacheFallback(customerId);
    }

    public List<ScoreResponse> getAuditHistory(String customerId) {
        try {
            return auditRepo.findByCustomerIdOrderByScoredAtDesc(customerId).stream()
                    .map(this::fromAuditEntity)
                    .toList();
        } catch (Exception e) {
            log.error("Failed to fetch audit history for {}: {}", customerId, e.getMessage());
            return List.of();
        }
    }

    private ScoreResponse tryCacheFallback(String customerId) {
        var cached = getCachedResult(customerId);
        if (cached != null) {
            log.info("Cache hit for {} (source: cache-hit)", customerId);
            return cached;
        }

        var stale = getStaleFromAudit(customerId);
        if (stale != null) {
            log.info("Stale cache fallback for {} (source: cache-fallback)", customerId);
            return stale;
        }

        log.warn("No cache or audit history for {} -> 503", customerId);
        throw new ScoringServiceUnavailableException(
            "Scoring unavailable for " + customerId + ". No cached result or audit history found.");
    }

    private void cacheResult(ScoreResponse result) {
        try {
            var key = redisKeyPrefix + result.customerId();
            var value = objectMapper.writeValueAsString(result);
            redisTemplate.opsForValue().set(key, value, cacheTtlMinutes, TimeUnit.MINUTES);
        } catch (Exception e) {
            log.warn("Failed to cache score for {}: {}", result.customerId(), e.getMessage());
        }
    }

    private ScoreResponse getCachedResult(String customerId) {
        try {
            var key = redisKeyPrefix + customerId;
            var cached = redisTemplate.opsForValue().get(key);
            if (cached != null && !cached.isEmpty()) {
                var r = objectMapper.readValue(cached, ScoreResponse.class);
                return new ScoreResponse(
                        r.customerId(), r.bucket(), r.probability(),
                        r.compositeScore(), r.features(), r.flags(),
                        r.shapExplanation(), r.modelVersion(),
                        "cache-hit", null, r.requestId(), r.scoredAt(),
                        r.businessName(), r.ownerName(), r.businessType(),
                        r.state(), r.requestedLoanAmount());
            }
        } catch (Exception e) {
            log.warn("Redis read failed for {}: {}", customerId, e.getMessage());
        }
        return null;
    }

    private ScoreResponse getStaleFromAudit(String customerId) {
        try {
            var entries = auditRepo.findByCustomerIdOrderByScoredAtDesc(customerId);
            if (!entries.isEmpty()) {
                return fromAuditEntity(entries.get(0));
            }
        } catch (Exception e) {
            log.warn("Audit read failed for {}: {}", customerId, e.getMessage());
        }
        return null;
    }

    private Map<String, Object> buildPredictRequest(CustomerProfile p) {
        var map = new LinkedHashMap<String, Object>();
        map.put("customer_id", p.getCustomerId());
        map.put("gst_registered", p.isGstRegistered());
        map.put("gst_monthly_turnover_avg", nullSafe(p.getGstMonthlyTurnoverAvg()));
        map.put("gst_filing_regularity", nullSafe(p.getGstFilingRegularity()));
        map.put("upi_monthly_txn_count", p.getUpiMonthlyTxnCount());
        map.put("upi_monthly_txn_value", nullSafe(p.getUpiMonthlyTxnValue()));
        map.put("electricity_monthly_units_avg", nullSafe(p.getElectricityMonthlyUnitsAvg()));
        map.put("electricity_payment_delay_days_avg", nullSafe(p.getElectricityPaymentDelayDaysAvg()));
        map.put("epfo_contribution_regularity", nullSafe(p.getEpfoContributionRegularity()));
        map.put("epfo_employee_count", p.getEpfoEmployeeCount());
        map.put("epfo_contribution_amount", nullSafe(p.getEpfoContributionAmount()));
        map.put("water_monthly_consumption_kl", nullSafe(p.getWaterMonthlyConsumptionKl()));
        map.put("water_payment_delay_days_avg", nullSafe(p.getWaterPaymentDelayDaysAvg()));
        map.put("fuel_monthly_spend_avg", nullSafe(p.getFuelMonthlySpendAvg()));
        map.put("fuel_spend_volatility", nullSafe(p.getFuelSpendVolatility()));
        map.put("requested_loan_amount", nullSafe(p.getRequestedLoanAmount()));
        map.put("years_in_operation", nullSafe(p.getYearsInOperation()));
        map.put("business_type", p.getBusinessType());
        return map;
    }

    private MlResult parseMlResponse(String body, String customerId) {
        try {
            var root = objectMapper.readTree(body);
            var result = root.get("result");

            var customerIdStr = result.get("customer_id").asText();
            var bucket = result.get("bucket").asText();
            var probability = result.get("probability").asDouble();
            var compositeScore = result.get("composite_score").asDouble();
            var modelVersion = result.get("model_version").asText();

            var featuresTree = result.get("features");
            var features = new LinkedHashMap<String, Double>();
            featuresTree.fieldNames().forEachRemaining(k ->
                features.put(k, featuresTree.get(k).asDouble()));

            var flagsTree = result.get("flags");
            var flags = parseFlags(flagsTree);

            ShapExplanation shapExp = null;
            var shapTree = result.get("shap_explanation");
            if (shapTree != null && !shapTree.isNull()) {
                shapExp = parseShap(shapTree);
            }

            return new MlResult(customerIdStr, bucket, probability, compositeScore,
                    features, flags, shapExp, modelVersion);
        } catch (Exception e) {
            throw new InvalidProfileDataException(
                "Failed to parse ML response for " + customerId + ": " + e.getMessage());
        }
    }

    private Flags parseFlags(com.fasterxml.jackson.databind.JsonNode f) {
        var isBlankSlate = f.get("is_blank_slate").asBoolean();

        var epfo = f.get("epfo_plausibility");
        var epfoFlag = new EpfoPlausibilityFlag(
                epfo.get("flag").asText(), epfo.get("message").asText(),
                epfo.has("implied_wage") && !epfo.get("implied_wage").isNull()
                        ? epfo.get("implied_wage").asDouble() : null,
                epfo.has("employee_count") && !epfo.get("employee_count").isNull()
                        ? epfo.get("employee_count").asInt() : null);

        var cap = f.get("capacity_flag");
        var capFlag = new CapacityFlag(
                cap.get("flag").asText(), cap.get("message").asText(),
                cap.has("loan_to_revenue_ratio") && !cap.get("loan_to_revenue_ratio").isNull()
                        ? cap.get("loan_to_revenue_ratio").asDouble() : null,
                cap.has("source") && !cap.get("source").isNull()
                        ? cap.get("source").asText() : null);

        var seas = f.get("seasonality_flags");
        var fuel = seas.get("fuel");
        var elec = seas.get("electricity");
        var fuelFlag = new SeasonalityFlag(
                fuel.get("flag").asText(), fuel.get("message").asText(),
                fuel.has("value") && !fuel.get("value").isNull() ? fuel.get("value").asDouble() : null,
                parseRange(fuel.get("expected_range")));
        var elecFlag = new SeasonalityFlag(
                elec.get("flag").asText(), elec.get("message").asText(),
                elec.has("value") && !elec.get("value").isNull() ? elec.get("value").asDouble() : null,
                parseRange(elec.get("expected_range")));

        return new Flags(isBlankSlate, epfoFlag, capFlag,
                new SeasonalityFlags(fuelFlag, elecFlag));
    }

    private Map<String, Double> parseRange(com.fasterxml.jackson.databind.JsonNode node) {
        if (node == null || node.isNull()) return null;
        var map = new LinkedHashMap<String, Double>();
        node.fieldNames().forEachRemaining(k -> map.put(k, node.get(k).asDouble()));
        return map;
    }

    private ShapExplanation parseShap(com.fasterxml.jackson.databind.JsonNode s) {
        var shapVals = new LinkedHashMap<String, Double>();
        var sv = s.get("shap_values");
        sv.fieldNames().forEachRemaining(k -> shapVals.put(k, sv.get(k).asDouble()));

        var baseVal = s.get("base_value").asDouble();
        var summary = s.get("human_readable_summary").asText();

        var ranks = new ArrayList<FeatureRank>();
        var fr = s.get("feature_ranking");
        for (var item : fr) {
            ranks.add(new FeatureRank(
                    item.get("feature_name").asText(),
                    item.get("value").asDouble(),
                    item.get("shap_value").asDouble(),
                    item.get("rank").asInt(),
                    item.get("direction").asText(),
                    item.get("business_description").asText(),
                    item.get("source").asText()));
        }

        return new ShapExplanation(shapVals, baseVal, ranks, summary);
    }

    private void persistAudit(ScoreResponse result, MlResult ml) {
        try {
            var audit = new AuditLogV2();
            audit.setCustomerId(result.customerId());
            audit.setBucket(result.bucket());
            audit.setConfidence(BigDecimal.valueOf(result.probability()));
            audit.setBlankSlateFlag(result.flags().isBlankSlate());
            audit.setModelVersion(result.modelVersion());
            audit.setShapReasons(objectMapper.writeValueAsString(
                    ml.shapExplanation != null ? ml.shapExplanation : Map.of()));
            audit.setCapacityFlag(objectMapper.writeValueAsString(
                    result.flags().capacityFlag() != null ? result.flags().capacityFlag() : Map.of()));
            audit.setEpfoFlag(objectMapper.writeValueAsString(
                    result.flags().epfoPlausibility() != null ? result.flags().epfoPlausibility() : Map.of()));
            audit.setSeasonalityFlags(objectMapper.writeValueAsString(
                    result.flags().seasonalityFlags() != null ? result.flags().seasonalityFlags() : Map.of()));
            audit.setSource(result.source());
            audit.setScoredAt(Instant.now());
            auditRepo.save(audit);
        } catch (Exception e) {
            log.warn("Failed to persist audit for {}: {}", result.customerId(), e.getMessage());
        }
    }

    private ScoreResponse fromAuditEntity(AuditLogV2 a) {
        try {
            var shapExp = a.getShapReasons() != null
                    ? objectMapper.readValue(a.getShapReasons(), ShapExplanation.class) : null;
            var capFlag = a.getCapacityFlag() != null
                    ? objectMapper.readValue(a.getCapacityFlag(), CapacityFlag.class)
                    : new CapacityFlag("unavailable", "", null, null);
            var epfoFlag = a.getEpfoFlag() != null
                    ? objectMapper.readValue(a.getEpfoFlag(), EpfoPlausibilityFlag.class)
                    : new EpfoPlausibilityFlag("unavailable", "", null, null);
            var seasFlags = a.getSeasonalityFlags() != null
                    ? objectMapper.readValue(a.getSeasonalityFlags(), SeasonalityFlags.class)
                    : new SeasonalityFlags(
                            new SeasonalityFlag("unavailable", "", null, null),
                            new SeasonalityFlag("unavailable", "", null, null));

            var prob = a.getConfidence() != null ? a.getConfidence().doubleValue() : 0.0;

            return new ScoreResponse(
                    a.getCustomerId(), a.getBucket(), prob, 0.0,
                    Map.of(), new Flags(a.isBlankSlateFlag(), epfoFlag, capFlag, seasFlags),
                    shapExp, a.getModelVersion(), "cache-fallback", a.getScoredAt(),
                    "", a.getScoredAt(),
                    null, null, null, null, null);
        } catch (Exception e) {
            log.warn("Failed to deserialize audit entity for {}: {}", a.getCustomerId(), e.getMessage());
            return null;
        }
    }

    private static Double nullSafe(BigDecimal v) {
        return v != null ? v.doubleValue() : null;
    }

    private record MlResult(
            String customerId, String bucket, double probability,
            double compositeScore, Map<String, Double> features,
            Flags flags, ShapExplanation shapExplanation,
            String modelVersion) {}
}
