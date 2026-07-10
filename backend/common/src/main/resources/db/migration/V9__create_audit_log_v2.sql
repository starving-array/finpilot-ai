CREATE TABLE audit_log_v2 (
    id               BIGSERIAL PRIMARY KEY,
    customer_id      VARCHAR(20) NOT NULL REFERENCES customer_profile(customer_id),
    bucket           VARCHAR(20) NOT NULL,
    confidence       NUMERIC(5,4),
    blank_slate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    model_version    VARCHAR(50) NOT NULL,
    shap_reasons     JSONB NOT NULL,
    capacity_flag    JSONB,
    epfo_flag        JSONB,
    seasonality_flags JSONB,
    source           VARCHAR(20) NOT NULL,
    scored_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_alv2_customer_id ON audit_log_v2 (customer_id);
CREATE INDEX idx_alv2_scored_at   ON audit_log_v2 (scored_at DESC);
