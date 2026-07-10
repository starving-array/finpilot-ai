package com.idbi.fhss.common.dto;

import com.idbi.fhss.common.enums.AuditAction;
import com.idbi.fhss.common.enums.Decision;
import java.time.Instant;
import java.util.UUID;

public record AuditLogEntry(
    UUID logId,
    UUID requestId,
    Instant timestamp,
    String actor,
    AuditAction action,
    String inputHash,
    String outputHash,
    String prevLogHash,
    Decision decision,
    String notes
) {}
