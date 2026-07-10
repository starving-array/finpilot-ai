CREATE TABLE feature_snapshot (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customer(customer_id),
    feature_vector JSONB NOT NULL,
    schema_version VARCHAR(20) NOT NULL,
    computation_version VARCHAR(20) NOT NULL,
    completeness_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    blank_slate_mode BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_snapshot_customer ON feature_snapshot(customer_id, created_at DESC);
CREATE INDEX idx_feature_snapshot_vector ON feature_snapshot USING gin(feature_vector);

-- Immutable: prevent updates and deletes
CREATE OR REPLACE FUNCTION prevent_feature_snapshot_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'feature_snapshot is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_feature_snapshot_immutable
    BEFORE UPDATE OR DELETE ON feature_snapshot
    FOR EACH ROW EXECUTE FUNCTION prevent_feature_snapshot_mutation();
