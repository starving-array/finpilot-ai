package com.idbi.fhss.common.observability;

import org.springframework.context.annotation.Configuration;

import io.micrometer.core.instrument.MeterRegistry;
import jakarta.annotation.PostConstruct;

@Configuration
public class MetricsConfig {

    private final MeterRegistry meterRegistry;

    public MetricsConfig(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    @PostConstruct
    public void registerCustomMetrics() {
        meterRegistry.gauge("scoring_requests_total",
                new java.util.concurrent.atomic.AtomicLong(0));
        meterRegistry.gauge("blank_slate_activation_rate",
                new java.util.concurrent.atomic.AtomicLong(0));
        meterRegistry.gauge("underwriter_agreement_rate",
                new java.util.concurrent.atomic.AtomicLong(0));
    }
}
