package com.idbi.fhss.customer;

import com.idbi.fhss.customer.entity.Customer;
import com.idbi.fhss.customer.repository.CustomerRepository;
import com.idbi.fhss.customer.service.CustomerService;
import com.idbi.fhss.common.exception.ResourceNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
class CustomerServiceTest {

    @Autowired
    private CustomerService customerService;

    @Autowired
    private CustomerRepository customerRepository;

    private UUID customerId;

    @BeforeEach
    void setUp() {
        customerRepository.deleteAll();
        var customer = new Customer();
        customer.setPan("SERVICETEST");
        customer.setName("Service Test");
        customer.setKycStatus("VERIFIED");
        customer.setTraditionalData("{\"gst\": {\"filing_regularity\": 0.9}}");
        customer.setAlternativeData("{\"epfo\": {\"contributions\": 100}}");
        customerId = customerRepository.save(customer).getCustomerId();
    }

    @Test
    void shouldSearchByName() {
        var results = customerService.search("Service");
        assertEquals(1, results.size());
        assertEquals("Service Test", results.get(0).name());
    }

    @Test
    void shouldReturnEmptyForShortQuery() {
        var results = customerService.search("S");
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldGetProfile() {
        var profile = customerService.getProfile(customerId);
        assertNotNull(profile);
        assertEquals("SERVICETEST", profile.pan());
        assertEquals("Service Test", profile.name());
    }

    @Test
    void shouldThrowForNotFound() {
        assertThrows(ResourceNotFoundException.class,
                () -> customerService.getProfile(UUID.randomUUID()));
    }

    @Test
    void shouldValidateCustomer() {
        var result = customerService.validateCustomer(customerId);
        assertTrue(result.valid());

        var badCustomer = new Customer();
        badCustomer.setPan("BADVALIDATE");
        badCustomer.setName("Bad Validate");
        badCustomer.setKycStatus("PENDING");
        var badId = customerRepository.save(badCustomer).getCustomerId();

        var badResult = customerService.validateCustomer(badId);
        assertFalse(badResult.valid());
        assertTrue(badResult.issues().stream().anyMatch(i -> i.contains("KYC")));
    }

    @Test
    void shouldUpdateCustomer() {
        var updated = customerService.updateCustomer(customerId, Map.of("name", "Updated Name"));
        assertEquals("Updated Name", updated.name());

        var profile = customerService.getProfile(customerId);
        assertEquals("Updated Name", profile.name());
    }
}
