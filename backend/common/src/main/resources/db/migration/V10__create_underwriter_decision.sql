CREATE TABLE underwriter_decision (
    id           BIGSERIAL    PRIMARY KEY,
    customer_id  VARCHAR(20)  NOT NULL REFERENCES customer_profile(customer_id),
    decision     VARCHAR(20)  NOT NULL CHECK (decision IN ('APPROVE','REVIEW','REJECT')),
    remarks      TEXT,
    reviewer     VARCHAR(100) NOT NULL DEFAULT 'underwriter',
    created_at   TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX idx_ud_customer_id ON underwriter_decision (customer_id);
CREATE INDEX idx_ud_decision    ON underwriter_decision (decision);
