CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE customer (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pan VARCHAR(10) NOT NULL,
    cin VARCHAR(21),
    name VARCHAR(255) NOT NULL,
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    traditional_data JSONB DEFAULT '{}'::jsonb,
    alternative_data JSONB DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_customer_pan ON customer(pan) WHERE deleted_at IS NULL;
CREATE INDEX idx_customer_name ON customer USING gin(name gin_trgm_ops);
CREATE INDEX idx_customer_created_at ON customer(created_at);
CREATE INDEX idx_customer_traditional_data ON customer USING gin(traditional_data);
CREATE INDEX idx_customer_alternative_data ON customer USING gin(alternative_data);
