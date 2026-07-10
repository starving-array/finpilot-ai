package com.idbi.fhss.scoring.exception;

public class CustomerNotFoundException extends FinancialHealthException {
    private final String customerId;

    public CustomerNotFoundException(String customerId) {
        super("CUSTOMER_NOT_FOUND", "Customer not found: " + customerId);
        this.customerId = customerId;
    }

    public String getCustomerId() {
        return customerId;
    }
}
