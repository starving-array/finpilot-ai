package com.idbi.fhss.scoring.controller;

import com.idbi.fhss.scoring.dto.CustomerProfileResponse;
import com.idbi.fhss.scoring.dto.DecisionRequest;
import com.idbi.fhss.scoring.dto.DecisionResponse;
import com.idbi.fhss.scoring.dto.ScoreResponse;
import com.idbi.fhss.scoring.service.DecisionService;
import com.idbi.fhss.scoring.service.ScoringClientService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/api/v1")
public class ScoreController {

    private static final Pattern CUSTOMER_ID_PATTERN = Pattern.compile("^CUST\\d{5}$");

    private final ScoringClientService scoringClientService;
    private final DecisionService decisionService;

    public ScoreController(ScoringClientService scoringClientService, DecisionService decisionService) {
        this.scoringClientService = scoringClientService;
        this.decisionService = decisionService;
    }

    @PostMapping("/score/{customerId}")
    public ResponseEntity<ScoreResponse> score(
            @PathVariable String customerId,
            @RequestParam(defaultValue = "false") boolean enableSeasonality,
            @RequestParam(required = false) Integer referenceMonth) {
        if (!CUSTOMER_ID_PATTERN.matcher(customerId).matches()) {
            throw new IllegalArgumentException("Invalid customerId format: " + customerId);
        }
        var response = scoringClientService.score(customerId, enableSeasonality, referenceMonth);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/score/audit/{customerId}")
    public ResponseEntity<List<ScoreResponse>> getAuditHistory(@PathVariable String customerId) {
        var history = scoringClientService.getAuditHistory(customerId);
        return ResponseEntity.ok(history);
    }

    @GetMapping("/customers/{customerId}/profile")
    public ResponseEntity<CustomerProfileResponse> getCustomerProfile(@PathVariable String customerId) {
        var profile = scoringClientService.getCustomerProfile(customerId);
        return ResponseEntity.ok(profile);
    }

    @PostMapping("/decisions")
    public ResponseEntity<DecisionResponse> submitDecision(@RequestBody DecisionRequest request) {
        var response = decisionService.submitDecision(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/decisions/{customerId}")
    public ResponseEntity<List<DecisionResponse>> getDecisions(@PathVariable String customerId) {
        var decisions = decisionService.getDecisions(customerId);
        return ResponseEntity.ok(decisions);
    }

    @GetMapping("/decisions/pending")
    public ResponseEntity<List<DecisionResponse>> getPendingReviews() {
        var pending = decisionService.getPendingReviews();
        return ResponseEntity.ok(pending);
    }

    @GetMapping("/score/health")
    public ResponseEntity<java.util.Map<String, Object>> health() {
        return ResponseEntity.ok(java.util.Map.of(
            "status", "UP",
            "service", "fhss-gateway",
            "timestamp", java.time.Instant.now().toString()
        ));
    }
}
