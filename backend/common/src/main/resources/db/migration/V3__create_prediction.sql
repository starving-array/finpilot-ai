CREATE TABLE prediction (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customer(customer_id),
    request_id UUID NOT NULL,
    category VARCHAR(20) NOT NULL,
    probabilities JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    feature_snapshot_id UUID REFERENCES feature_snapshot(snapshot_id),
    blank_slate_mode BOOLEAN NOT NULL DEFAULT FALSE,
    business_rules_applied JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_prediction_request_id ON prediction(request_id);
CREATE INDEX idx_prediction_customer ON prediction(customer_id, created_at DESC);

-- Immutable trigger
CREATE TRIGGER trg_prediction_immutable
    BEFORE UPDATE OR DELETE ON prediction
    FOR EACH ROW EXECUTE FUNCTION prevent_feature_snapshot_mutation();
