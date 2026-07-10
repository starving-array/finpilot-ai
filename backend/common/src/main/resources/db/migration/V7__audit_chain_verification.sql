CREATE OR REPLACE FUNCTION verify_audit_chain(
    from_timestamp TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    to_timestamp TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE(
    broken_log_id UUID,
    expected_prev_hash VARCHAR(64),
    actual_prev_hash VARCHAR(64),
    log_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    WITH ordered_logs AS (
        SELECT
            log_id,
            output_hash,
            prev_log_hash,
            timestamp,
            LAG(output_hash) OVER (ORDER BY log_id) AS expected_prev_hash
        FROM audit_log
        WHERE timestamp BETWEEN from_timestamp AND to_timestamp
    )
    SELECT
        ordered_logs.log_id,
        ordered_logs.expected_prev_hash,
        ordered_logs.prev_log_hash,
        ordered_logs.timestamp
    FROM ordered_logs
    WHERE ordered_logs.prev_log_hash IS DISTINCT FROM ordered_logs.expected_prev_hash
      AND ordered_logs.log_id != (SELECT MIN(log_id) FROM audit_log);
END;
$$ LANGUAGE plpgsql;
