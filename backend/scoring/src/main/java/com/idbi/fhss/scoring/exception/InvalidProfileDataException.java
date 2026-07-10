package com.idbi.fhss.scoring.exception;

public class InvalidProfileDataException extends FinancialHealthException {
    public InvalidProfileDataException(String message) {
        super("INVALID_PROFILE_DATA", message);
    }
}
