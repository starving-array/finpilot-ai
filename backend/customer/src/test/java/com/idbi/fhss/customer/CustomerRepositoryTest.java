package com.idbi.fhss.customer;

import com.idbi.fhss.customer.entity.Customer;
import com.idbi.fhss.customer.repository.CustomerRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class CustomerRepositoryTest {

    @Autowired
    private CustomerRepository customerRepository;

    @Test
    void shouldSaveAndFindCustomer() {
        var customer = new Customer();
        customer.setPan("ABCDE1234F");
        customer.setName("Test Business");
        customer.setKycStatus("VERIFIED");
        customer.setTraditionalData("{\"gst\": {\"filing_regularity\": 0.95}}");
        customer.setAlternativeData("{\"electricity\": {\"avg_consumption\": 500}}");

        var saved = customerRepository.save(customer);
        assertNotNull(saved.getCustomerId());
        assertNotNull(saved.getCreatedAt());

        var found = customerRepository.findByPanAndDeletedAtIsNull("ABCDE1234F");
        assertTrue(found.isPresent());
        assertEquals("Test Business", found.get().getName());
    }

    @Test
    void shouldSearchCustomers() {
        var c1 = new Customer();
        c1.setPan("AAAAA1111A");
        c1.setName("Alpha Enterprises");
        c1.setKycStatus("VERIFIED");
        customerRepository.save(c1);

        var c2 = new Customer();
        c2.setPan("BBBBB2222B");
        c2.setName("Beta Solutions");
        c2.setKycStatus("PENDING");
        customerRepository.save(c2);

        var results = customerRepository.search("Alpha");
        assertEquals(1, results.size());
        assertEquals("Alpha Enterprises", results.get(0).getName());

        results = customerRepository.search("1111");
        assertEquals(1, results.size());

        results = customerRepository.search("zzz");
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldNotFindDeletedCustomer() {
        var customer = new Customer();
        customer.setPan("ZZZZZ9999Z");
        customer.setName("To Delete");
        customer.setKycStatus("VERIFIED");
        var saved = customerRepository.save(customer);

        saved.setDeletedAt(java.time.Instant.now());
        customerRepository.save(saved);

        var found = customerRepository.findByPanAndDeletedAtIsNull("ZZZZZ9999Z");
        assertTrue(found.isEmpty());
    }

    @Test
    void shouldEnforceUniquePan() {
        var c1 = new Customer();
        c1.setPan("UNIQUE1234X");
        c1.setName("First");
        c1.setKycStatus("VERIFIED");
        customerRepository.save(c1);

        var c2 = new Customer();
        c2.setPan("UNIQUE1234X");
        c2.setName("Second");
        c2.setKycStatus("VERIFIED");

        assertThrows(Exception.class, () -> customerRepository.save(c2));
    }

    @Test
    void shouldDetectPanExists() {
        var customer = new Customer();
        customer.setPan("EXIST1234E");
        customer.setName("Exists Check");
        customer.setKycStatus("VERIFIED");
        customerRepository.save(customer);

        assertTrue(customerRepository.existsByPanAndDeletedAtIsNull("EXIST1234E"));
        assertFalse(customerRepository.existsByPanAndDeletedAtIsNull("NONEXIST1X"));
    }

    @Test
    void shouldReturnEmptyForShortQuery() {
        var results = customerRepository.search("A");
        assertTrue(results.isEmpty());
    }

    @Test
    void shouldHandleJsonbData() {
        var customer = new Customer();
        customer.setPan("JSONB1234J");
        customer.setName("JSONB Test");
        customer.setKycStatus("VERIFIED");
        customer.setTraditionalData("{\"gst\": {\"filing_regularity\": 0.87, " +
                "\"tax_growth_yoy\": 0.12}, \"upi\": {\"txn_volume_30d\": 150}}");
        customerRepository.save(customer);

        var found = customerRepository.findByPanAndDeletedAtIsNull("JSONB1234J");
        assertTrue(found.isPresent());
        assertNotNull(found.get().getTraditionalData());
        assertTrue(found.get().getTraditionalData().contains("filing_regularity"));
    }

    @Test
    void shouldRejectNullPan() {
        var customer = new Customer();
        customer.setName("No PAN");
        customer.setKycStatus("PENDING");
        assertThrows(Exception.class, () -> customerRepository.save(customer));
    }

    @Test
    void shouldRejectNullName() {
        var customer = new Customer();
        customer.setPan("NONAME123N");
        customer.setKycStatus("PENDING");
        assertThrows(Exception.class, () -> customerRepository.save(customer));
    }
}
