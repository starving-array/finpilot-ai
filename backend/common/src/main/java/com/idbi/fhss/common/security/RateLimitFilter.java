package com.idbi.fhss.common.security;

import java.time.Instant;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Component
@ConditionalOnBean(StringRedisTemplate.class)
public class RateLimitFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RateLimitFilter.class);

    private final StringRedisTemplate redis;
    private final int maxRequestsPerMinute;

    public RateLimitFilter(StringRedisTemplate redis,
                           @Value("${app.rate-limit.max-per-minute:100}") int maxRequestsPerMinute) {
        this.redis = redis;
        this.maxRequestsPerMinute = maxRequestsPerMinute;
    }

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain filterChain)
            throws ServletException, IOException {

        if (request.getRequestURI().startsWith("/actuator")) {
            filterChain.doFilter(request, response);
            return;
        }

        var userId = request.getUserPrincipal() != null ? request.getUserPrincipal().getName() : "anonymous";
        var endpoint = request.getRequestURI();
        var key = "rate_limit:" + userId + ":" + endpoint;

        try {
            var script = """
                local key = KEYS[1]
                local limit = tonumber(ARGV[1])
                local current = redis.call('INCR', key)
                if current == 1 then
                    redis.call('EXPIRE', key, 60)
                end
                return current
                """;

            var redisScript = new org.springframework.data.redis.core.script.DefaultRedisScript<Long>(script, Long.class);
            var current = redis.execute(redisScript, List.of(key), String.valueOf(maxRequestsPerMinute));

            if (current > maxRequestsPerMinute) {
                response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
                response.setHeader("Retry-After", "60");
                response.getWriter().write("{\"error\":\"Rate limit exceeded. Retry after 60 seconds.\"}");
                return;
            }
        } catch (Exception e) {
            log.warn("Rate limiting unavailable (Redis down?), allowing request: {}", e.getMessage());
        }

        filterChain.doFilter(request, response);
    }
}
