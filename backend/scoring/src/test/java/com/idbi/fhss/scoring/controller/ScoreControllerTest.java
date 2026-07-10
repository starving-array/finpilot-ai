package com.idbi.fhss.scoring.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.scoring.dto.CustomerProfileResponse;
import com.idbi.fhss.scoring.dto.DecisionRequest;
import com.idbi.fhss.scoring.dto.DecisionResponse;
import com.idbi.fhss.scoring.dto.ScoreResponse;
import com.idbi.fhss.scoring.exception.CustomerNotFoundException;
import com.idbi.fhss.scoring.exception.ScoringServiceUnavailableException;
import com.idbi.fhss.scoring.service.DecisionService;
import com.idbi.fhss.scoring.service.ScoringClientService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ScoreController.class)
class ScoreControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @MockitoBean private ScoringClientService scoringClientService;
    @MockitoBean private DecisionService decisionService;

    @Test
    void score_shouldReturn200() throws Exception {
        var response = createScoreResponse();
        when(scoringClientService.score("CUST00001")).thenReturn(response);

        mockMvc.perform(post("/api/v1/score/{customerId}", "CUST00001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.customerId").value("CUST00001"))
                .andExpect(jsonPath("$.bucket").value("disciplined"))
                .andExpect(jsonPath("$.source").value("live"));
    }

    @Test
    void score_shouldReturn404WhenCustomerNotFound() throws Exception {
        when(scoringClientService.score("UNKNOWN"))
                .thenThrow(new CustomerNotFoundException("UNKNOWN"));

        mockMvc.perform(post("/api/v1/score/{customerId}", "UNKNOWN"))
                .andExpect(status().isNotFound());
    }

    @Test
    void score_shouldReturn503WhenServiceUnavailable() throws Exception {
        when(scoringClientService.score("CUST99999"))
                .thenThrow(new ScoringServiceUnavailableException("ML service down"));

        mockMvc.perform(post("/api/v1/score/{customerId}", "CUST99999"))
                .andExpect(status().isServiceUnavailable());
    }

    @Test
    void getAuditHistory_shouldReturnList() throws Exception {
        var response = createScoreResponse();
        when(scoringClientService.getAuditHistory("CUST00001"))
                .thenReturn(List.of(response));

        mockMvc.perform(get("/api/v1/score/audit/{customerId}", "CUST00001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].customerId").value("CUST00001"));
    }

    @Test
    void getAuditHistory_shouldReturnEmptyForUnknown() throws Exception {
        when(scoringClientService.getAuditHistory("UNKNOWN"))
                .thenReturn(List.of());

        mockMvc.perform(get("/api/v1/score/audit/{customerId}", "UNKNOWN"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void getCustomerProfile_shouldReturnProfile() throws Exception {
        var profile = new CustomerProfileResponse(
                "CUST00001", "Test Business", "Owner", "retail",
                "Maharashtra", 5.0, 500000.0, false, 0.85);
        when(scoringClientService.getCustomerProfile("CUST00001")).thenReturn(profile);

        mockMvc.perform(get("/api/v1/customers/{customerId}/profile", "CUST00001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.customer_id").value("CUST00001"))
                .andExpect(jsonPath("$.business_name").value("Test Business"));
    }

    @Test
    void getCustomerProfile_shouldReturn404WhenNotFound() throws Exception {
        when(scoringClientService.getCustomerProfile("UNKNOWN"))
                .thenThrow(new CustomerNotFoundException("UNKNOWN"));

        mockMvc.perform(get("/api/v1/customers/{customerId}/profile", "UNKNOWN"))
                .andExpect(status().isNotFound());
    }

    @Test
    void submitDecision_shouldReturn200() throws Exception {
        var request = new DecisionRequest("CUST00001", "APPROVE", "Good profile");
        var response = new DecisionResponse(1L, "CUST00001", "APPROVE",
                "Good profile", "underwriter", Instant.now());
        when(decisionService.submitDecision(any())).thenReturn(response);

        mockMvc.perform(post("/api/v1/decisions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.decision").value("APPROVE"));
    }

    @Test
    void submitDecision_shouldReturn422WhenInvalid() throws Exception {
        mockMvc.perform(post("/api/v1/decisions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getDecisions_shouldReturnList() throws Exception {
        var response = new DecisionResponse(1L, "CUST00001", "APPROVE",
                "Good", "underwriter", Instant.now());
        when(decisionService.getDecisions("CUST00001")).thenReturn(List.of(response));

        mockMvc.perform(get("/api/v1/decisions/{customerId}", "CUST00001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].decision").value("APPROVE"));
    }

    @Test
    void getPendingReviews_shouldReturnList() throws Exception {
        var response = new DecisionResponse(1L, "CUST00042", "REVIEW",
                "Needs review", "underwriter", Instant.now());
        when(decisionService.getPendingReviews()).thenReturn(List.of(response));

        mockMvc.perform(get("/api/v1/decisions/pending"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].decision").value("REVIEW"));
    }

    @Test
    void health_shouldReturn200() throws Exception {
        mockMvc.perform(get("/api/v1/score/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("fhss-gateway"));
    }

    private ScoreResponse createScoreResponse() {
        return new ScoreResponse(
                "CUST00001", "disciplined", 0.85, 0.78,
                Map.of("payment_regularity", 0.9),
                new ScoreResponse.Flags(false,
                        new ScoreResponse.EpfoPlausibilityFlag("plausible", "OK", 15000.0, 10),
                        new ScoreResponse.CapacityFlag("normal", "OK", 0.4, "gst"),
                        new ScoreResponse.SeasonalityFlags(
                                new ScoreResponse.SeasonalityFlag("normal", "OK", 0.2, null),
                                new ScoreResponse.SeasonalityFlag("normal", "OK", 0.1, null))),
                new ScoreResponse.ShapExplanation(
                        Map.of("payment_regularity", 0.3), 0.5,
                        List.of(new ScoreResponse.FeatureRank("payment_regularity", 0.9, 0.3, 1,
                                "positive", "Good payment", "standard")),
                        "Summary"),
                "2.0.0", "live", null, "req-001", Instant.now(),
                "Test Business", "Owner", "retail", "Maharashtra", 500000.0);
    }
}
