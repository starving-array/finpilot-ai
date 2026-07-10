package com.idbi.fhss.common.dto;

import java.util.List;

public record ValidationResult(
    boolean valid,
    List<String> issues
) {}
