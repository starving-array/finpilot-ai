CREATE TABLE business_rule (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    condition_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    priority INT NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default business rules
INSERT INTO business_rule (name, description, condition_json, action_json, priority, enabled, created_by) VALUES
('Low Confidence Rule',
 'Route to manual review when confidence is below 60%',
 '{"type": "comparison", "field": "confidence", "operator": "lt", "value": 60}',
 '{"action": "manual_review", "badge": "low_confidence", "message": "Confidence below threshold — mandatory manual review required"}',
 100, TRUE, 'system'),

('Blank-Slate Activation',
 'Activate blank-slate mode when traditional data completeness is low',
 '{"type": "comparison", "field": "traditional_completeness", "operator": "lt", "value": 0.3}',
 '{"action": "activate_blank_slate", "badge": "blank_slate", "message": "Traditional data insufficient — using alternative signals with higher weight"}',
 90, TRUE, 'system'),

('Missing Critical Features',
 'Reject automatic scoring when both electricity and EPFO data are missing',
 '{"type": "and", "conditions": [{"type": "is_null", "field": "electricity_consumption"}, {"type": "is_null", "field": "epfo_contributions"}]}',
 '{"action": "reject_auto", "badge": "insufficient_data", "message": "Both electricity and EPFO data missing — insufficient signals for scoring"}',
 80, TRUE, 'system'),

('Regulatory Flag',
 'Mandatory human approval for regulated sectors',
 '{"type": "in", "field": "sector", "values": ["NBFC", "Real Estate", "Financial Services"]}',
 '{"action": "mandatory_human_approval", "badge": "regulatory", "message": "Sector requires mandatory human approval per regulatory policy"}',
 70, TRUE, 'system'),

('Borderline Category',
 'Flag cases where top two categories are within 5% margin',
 '{"type": "comparison", "field": "probability_margin", "operator": "lt", "value": 0.05}',
 '{"action": "flag_borderline", "badge": "borderline", "message": "Near-equal probabilities between top categories — manual review recommended"}',
 60, TRUE, 'system');
