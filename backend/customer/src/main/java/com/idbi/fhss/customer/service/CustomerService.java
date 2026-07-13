package com.idbi.fhss.customer.service;

import com.idbi.fhss.common.dto.CustomerProfileDTO;
import com.idbi.fhss.common.dto.ValidationResult;
import com.idbi.fhss.common.exception.ResourceNotFoundException;
import com.idbi.fhss.customer.entity.Customer;
import com.idbi.fhss.customer.repository.CustomerRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@Transactional(readOnly = true)
public class CustomerService {

    private static final Logger log = LoggerFactory.getLogger(CustomerService.class);

    private static final String CACHE_PREFIX = "customer:profile:";
    private static final long CACHE_TTL_SECONDS = 300;

    private final CustomerRepository customerRepository;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public CustomerService(CustomerRepository customerRepository,
                           ObjectProvider<StringRedisTemplate> redisProvider,
                           ObjectMapper objectMapper) {
        this.customerRepository = customerRepository;
        this.redis = redisProvider.getIfAvailable();
        this.objectMapper = objectMapper;
    }

    public List<CustomerProfileDTO> search(String query) {
        if (query == null || query.trim().length() < 2) {
            log.debug("Search query too short (min 2 chars): '{}'", query);
            return List.of();
        }
        long start = System.currentTimeMillis();
        var results = customerRepository.search(query.trim())
                .stream()
                .map(this::toProfileDTO)
                .toList();
        log.info("Customer search '{}' returned {} results in {}ms", query.trim(), results.size(),
            System.currentTimeMillis() - start);
        return results;
    }

    public CustomerProfileDTO getProfile(UUID customerId) {
        long start = System.currentTimeMillis();
        var cacheKey = CACHE_PREFIX + customerId;
        if (redis != null) {
            try {
                var cached = redis.opsForValue().get(cacheKey);
                if (cached != null) {
                    try {
                        var dto = objectMapper.readValue(cached, CustomerProfileDTO.class);
                        log.debug("Customer profile cache HIT for {} ({}ms)", customerId, System.currentTimeMillis() - start);
                        return dto;
                    } catch (Exception e) {
                        log.debug("Customer profile cache deserialization failed for {}, falling through to DB", customerId);
                    }
                }
            } catch (Exception e) {
                log.debug("Cache read failed for customer {}, falling through to DB: {}", customerId, e.getMessage());
            }
        }
        var customer = findActive(customerId);
        var dto = toProfileDTO(customer);
        if (redis != null) {
            try {
                redis.opsForValue().set(cacheKey, objectMapper.writeValueAsString(dto), CACHE_TTL_SECONDS, TimeUnit.SECONDS);
            } catch (Exception e) {
                log.debug("Cache write failed for customer {}: {}", customerId, e.getMessage());
            }
        }
        log.debug("Customer profile loaded from DB for {} ({}ms)", customerId, System.currentTimeMillis() - start);
        return dto;
    }

    public ValidationResult validateCustomer(UUID customerId) {
        var customer = findActive(customerId);
        var issues = new java.util.ArrayList<String>();
        if (!"VERIFIED".equals(customer.getKycStatus())) {
            issues.add("KYC status is " + customer.getKycStatus());
        }
        if (customer.getTraditionalData() == null || customer.getTraditionalData().isBlank()) {
            issues.add("No traditional data available");
        }
        if (customer.getAlternativeData() == null || customer.getAlternativeData().isBlank()) {
            issues.add("No alternative data available");
        }
        return new ValidationResult(issues.isEmpty(), issues);
    }

    @Transactional
    public CustomerProfileDTO updateCustomer(UUID customerId, Map<String, Object> updates) {
        var customer = findActive(customerId);
        if (updates.containsKey("name")) {
            customer.setName((String) updates.get("name"));
        }
        if (updates.containsKey("kycStatus")) {
            customer.setKycStatus((String) updates.get("kycStatus"));
        }
        if (updates.containsKey("traditionalData")) {
            try {
                customer.setTraditionalData(objectMapper.writeValueAsString(updates.get("traditionalData")));
            } catch (Exception e) {
                throw new RuntimeException("Failed to serialize traditional data", e);
            }
        }
        if (updates.containsKey("alternativeData")) {
            try {
                customer.setAlternativeData(objectMapper.writeValueAsString(updates.get("alternativeData")));
            } catch (Exception e) {
                throw new RuntimeException("Failed to serialize alternative data", e);
            }
        }
        customerRepository.save(customer);
        if (redis != null) {
            try {
                var cacheKey = CACHE_PREFIX + customerId;
                redis.delete(cacheKey);
            } catch (Exception e) {
                log.debug("Cache delete failed for customer {}: {}", customerId, e.getMessage());
            }
        }
        return toProfileDTO(customer);
    }

    private Customer findActive(UUID customerId) {
        return customerRepository.findByCustomerIdAndDeletedAtIsNull(customerId)
                .orElseThrow(() -> new ResourceNotFoundException("Customer", customerId.toString()));
    }

    private CustomerProfileDTO toProfileDTO(Customer c) {
        Map<String, Object> traditional = Map.of();
        Map<String, Object> alternative = Map.of();
        try {
            if (c.getTraditionalData() != null && !c.getTraditionalData().isBlank()) {
                traditional = objectMapper.readValue(c.getTraditionalData(), new TypeReference<>() {});
            }
            if (c.getAlternativeData() != null && !c.getAlternativeData().isBlank()) {
                alternative = objectMapper.readValue(c.getAlternativeData(), new TypeReference<>() {});
            }
        } catch (Exception e) {
            // deserialization failure, return empty maps
        }
        return new CustomerProfileDTO(
                c.getCustomerId(), c.getPan(), c.getCin(), c.getName(),
                c.getKycStatus(), traditional, alternative,
                c.getVersion(), c.getCreatedAt(), c.getUpdatedAt()
        );
    }
}
