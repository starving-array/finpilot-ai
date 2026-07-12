ALTER TABLE audit_log_v2
    ADD COLUMN composite_score NUMERIC(5,4),
    ADD COLUMN features JSONB,
    ADD COLUMN request_id VARCHAR(16),
    ADD COLUMN business_name VARCHAR(200),
    ADD COLUMN owner_name VARCHAR(200),
    ADD COLUMN business_type VARCHAR(50),
    ADD COLUMN state VARCHAR(50),
    ADD COLUMN requested_loan_amount NUMERIC(14,2);
