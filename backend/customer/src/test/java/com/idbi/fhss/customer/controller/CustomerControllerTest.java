package com.idbi.fhss.customer.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.idbi.fhss.customer.entity.Customer;
import com.idbi.fhss.customer.repository.CustomerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;
import java.util.UUID;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class CustomerControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CustomerRepository customerRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private UUID customerId;

    @BeforeEach
    void setUp() {
        customerRepository.deleteAll();
        var customer = new Customer();
        customer.setPan("CONTRL1234C");
        customer.setName("Controller Test");
        customer.setKycStatus("VERIFIED");
        customerId = customerRepository.save(customer).getCustomerId();
    }

    @Test
    void shouldSearchCustomers() throws Exception {
        mockMvc.perform(get("/api/v1/customers/search")
                        .param("q", "Controller"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].name").value("Controller Test"));
    }

    @Test
    void shouldReturnEmptyForNoMatch() throws Exception {
        mockMvc.perform(get("/api/v1/customers/search")
                        .param("q", "zzz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void shouldGetCustomerProfile() throws Exception {
        mockMvc.perform(get("/api/v1/customers/{id}", customerId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pan").value("CONTRL1234C"))
                .andExpect(jsonPath("$.name").value("Controller Test"));
    }

    @Test
    void shouldReturn404ForMissingCustomer() throws Exception {
        mockMvc.perform(get("/api/v1/customers/{id}", UUID.randomUUID()))
                .andExpect(status().isNotFound());
    }

    @Test
    void shouldUpdateCustomer() throws Exception {
        var updates = Map.of("name", "Updated Controller");
        mockMvc.perform(put("/api/v1/customers/{id}", customerId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updates)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Updated Controller"));
    }
}
