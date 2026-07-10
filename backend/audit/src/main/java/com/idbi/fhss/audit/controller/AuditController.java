package com.idbi.fhss.audit.controller;

import com.idbi.fhss.audit.entity.AuditLog;
import com.idbi.fhss.audit.repository.AuditLogRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/audit")
public class AuditController {

    private final AuditLogRepository auditLogRepository;

    public AuditController(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @GetMapping
    public ResponseEntity<List<AuditLog>> getAuditLog(@RequestParam("customerId") UUID customerId) {
        var entries = auditLogRepository.findByCustomerIdOrderByTimestampDesc(customerId);
        return ResponseEntity.ok(entries);
    }
}
