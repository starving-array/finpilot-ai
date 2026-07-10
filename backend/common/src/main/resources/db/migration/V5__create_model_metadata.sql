CREATE TABLE model_metadata (
    model_version VARCHAR(20) PRIMARY KEY,
    training_date TIMESTAMPTZ,
    dataset_hash VARCHAR(64),
    metrics JSONB DEFAULT '{}'::jsonb,
    feature_schema JSONB DEFAULT '[]'::jsonb,
    artifact_path VARCHAR(500),
    deployed_at TIMESTAMPTZ,
    deployed_by VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'INACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
