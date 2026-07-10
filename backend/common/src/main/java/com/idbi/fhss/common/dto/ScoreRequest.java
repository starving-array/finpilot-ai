package com.idbi.fhss.common.dto;

import jakarta.validation.constraints.NotNull;
import java.util.UUID;

public record ScoreRequest(
    @NotNull UUID customerId,
    @NotNull UUID requestId
) {}
