package com.idbi.fhss.common.observability;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.data.redis.core.StringRedisTemplate;

import io.micrometer.core.instrument.MeterRegistry;

@Configuration
public class ObservabilityConfig {

    @Bean
    public HealthIndicator redisHealth(StringRedisTemplate redis) {
        return () -> {
            try {
                redis.opsForValue().get("healthcheck");
                return org.springframework.boot.actuate.health.Health.up().build();
            } catch (Exception e) {
                return org.springframework.boot.actuate.health.Health.down(e).build();
            }
        };
    }
}
