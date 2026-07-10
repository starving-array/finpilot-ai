package com.idbi.fhss.customer.controller;

import com.idbi.fhss.common.dto.CustomerProfileDTO;
import com.idbi.fhss.customer.service.CustomerService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/customers")
public class CustomerController {

    private final CustomerService customerService;

    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    @GetMapping("/search")
    public ResponseEntity<List<CustomerProfileDTO>> search(@RequestParam("q") String query) {
        var results = customerService.search(query);
        return ResponseEntity.ok(results);
    }

    @GetMapping("/{id}")
    public ResponseEntity<CustomerProfileDTO> getProfile(@PathVariable("id") UUID customerId) {
        var profile = customerService.getProfile(customerId);
        return ResponseEntity.ok(profile);
    }

    @PutMapping("/{id}")
    public ResponseEntity<CustomerProfileDTO> updateProfile(
            @PathVariable("id") UUID customerId,
            @RequestBody Map<String, Object> updates) {
        var profile = customerService.updateCustomer(customerId, updates);
        return ResponseEntity.ok(profile);
    }
}
