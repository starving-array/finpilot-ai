CREATE TABLE customer_profile (
    customer_id                          VARCHAR(20) PRIMARY KEY,
    business_name                        VARCHAR(200) NOT NULL,
    owner_name                           VARCHAR(200),
    business_type                        VARCHAR(50)  NOT NULL,
    state                                VARCHAR(50),
    years_in_operation                   NUMERIC(4,1),

    -- Standard data (null or sparse for blank-slate profiles)
    gst_registered                       BOOLEAN NOT NULL DEFAULT FALSE,
    gst_monthly_turnover_avg             NUMERIC(14,2),
    gst_filing_regularity                NUMERIC(3,2),

    -- UPI data
    upi_monthly_txn_count                INTEGER,
    upi_monthly_txn_value                NUMERIC(14,2),

    -- Alternative data (always collected)
    electricity_monthly_units_avg        NUMERIC(10,2),
    electricity_payment_delay_days_avg   NUMERIC(6,2),
    epfo_contribution_regularity         NUMERIC(3,2),
    epfo_employee_count                  INTEGER,
    epfo_contribution_amount             NUMERIC(14,2),
    water_monthly_consumption_kl         NUMERIC(10,2),
    water_payment_delay_days_avg         NUMERIC(6,2),
    fuel_monthly_spend_avg               NUMERIC(14,2),
    fuel_spend_volatility                NUMERIC(5,2),
    requested_loan_amount                NUMERIC(14,2),

    -- Flags
    is_blank_slate                       BOOLEAN NOT NULL DEFAULT FALSE,

    created_at                           TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_cp_business_type  ON customer_profile (business_type);
CREATE INDEX idx_cp_blank_slate    ON customer_profile (is_blank_slate);
