package com.idbi.fhss.customer.repository;

import com.idbi.fhss.customer.entity.Customer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface CustomerRepository extends JpaRepository<Customer, UUID> {

    Optional<Customer> findByPanAndDeletedAtIsNull(String pan);

    @Query("SELECT c FROM Customer c WHERE c.deletedAt IS NULL AND " +
           "(LOWER(c.pan) LIKE LOWER(CONCAT('%', :q, '%')) OR " +
           "LOWER(c.name) LIKE LOWER(CONCAT('%', :q, '%')) OR " +
           "LOWER(c.cin) LIKE LOWER(CONCAT('%', :q, '%')))")
    List<Customer> search(@Param("q") String query);

    Optional<Customer> findByCustomerIdAndDeletedAtIsNull(UUID customerId);

    boolean existsByPanAndDeletedAtIsNull(String pan);
}
