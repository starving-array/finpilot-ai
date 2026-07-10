import type { ScoreResponse } from '../types'

export const MOCK_SCORE_RESPONSE: ScoreResponse = {
  customerId: 'CUST00042',
  bucket: 'disciplined',
  probability: 0.85,
  composite_score: 0.78,
  features: {
    payment_regularity: 0.9,
    financial_capacity_proxy: 0.75,
    business_longevity: 0.8,
    data_coverage: 0.7,
    evidence_confidence: 0.85,
    is_blank_slate_flag: 0,
  },
  flags: {
    is_blank_slate: false,
    epfo_plausibility: { flag: 'plausible', message: 'EPFO data is plausible', implied_wage: 15000, employee_count: 10 },
    capacity_flag: { flag: 'normal', message: 'Loan amount is within capacity', loan_to_revenue_ratio: 0.4, source: 'gst' },
    seasonality_flags: {
      fuel: { flag: 'normal', message: 'Fuel volatility within range', value: 0.2, expected_range: { lo: 0, hi: 0.3 } },
      electricity: { flag: 'normal', message: 'Electricity volatility within range', value: 0.1, expected_range: { lo: 0, hi: 0.3 } },
    },
  },
  shap_explanation: {
    shap_values: { payment_regularity: 0.3, financial_capacity_proxy: 0.2 },
    base_value: 0.5,
    feature_ranking: [
      { feature_name: 'payment_regularity', value: 0.9, shap_value: 0.3, rank: 1, direction: 'positive', business_description: 'Consistent payment behavior', source: 'standard' },
      { feature_name: 'financial_capacity_proxy', value: 0.75, shap_value: 0.2, rank: 2, direction: 'positive', business_description: 'Strong financial capacity', source: 'mixed' },
    ],
    human_readable_summary: 'Assessment based on mixed traditional and alternative data.',
  },
  model_version: '2.0.0',
  source: 'live',
  stale_since: null,
  request_id: 'req-001',
  scored_at: '2026-07-10T10:00:00Z',
  business_name: 'Ramesh Traders',
  owner_name: 'Ramesh Kumar',
  business_type: 'retail',
  state: 'Maharashtra',
  requested_loan_amount: 500000,
}

export function createMockFetch(data: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}
