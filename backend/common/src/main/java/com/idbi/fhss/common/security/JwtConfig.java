package com.idbi.fhss.common.security;

import javax.crypto.SecretKey;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import io.jsonwebtoken.security.Keys;

@Configuration
public class JwtConfig {

    @Value("${app.jwt.secret:change-this-secret-in-production-minimum-32-chars!!}")
    private String secret;

    @Value("${app.jwt.expiration-minutes:15}")
    private int expirationMinutes;

    @Value("${app.jwt.refresh-expiration-days:7}")
    private int refreshExpirationDays;

    @Bean
    public SecretKey signingKey() {
        return Keys.hmacShaKeyFor(secret.getBytes());
    }

    public SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secret.getBytes());
    }

    public int getExpirationMinutes() {
        return expirationMinutes;
    }

    public int getRefreshExpirationDays() {
        return refreshExpirationDays;
    }
}
