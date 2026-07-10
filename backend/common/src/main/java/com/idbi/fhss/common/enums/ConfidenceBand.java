package com.idbi.fhss.common.enums;

public enum ConfidenceBand {
    HIGH(80, 100),
    MEDIUM(60, 79),
    LOW(40, 59),
    VERY_LOW(0, 39);

    private final int min;
    private final int max;

    ConfidenceBand(int min, int max) {
        this.min = min;
        this.max = max;
    }

    public int getMin() { return min; }
    public int getMax() { return max; }

    public static ConfidenceBand fromConfidence(double confidence) {
        int c = (int) Math.round(confidence);
        for (ConfidenceBand band : values()) {
            if (c >= band.min && c <= band.max) {
                return band;
            }
        }
        return VERY_LOW;
    }
}
