export type Status = 'idle' | 'loading' | 'success' | 'stale' | 'notFound' | 'serviceDegraded' | 'error'

export interface AppState {
  status: Status
  customerId: string
  result: ScoreResponse | null
  profile: CustomerProfileResponse | null
  error: string | null
}

export interface ScoreResponse {
  customerId: string
  bucket: string
  probability: number
  composite_score: number
  features: Record<string, number>
  flags: Flags
  shap_explanation: ShapExplanation | null
  model_version: string
  source: string
  stale_since: string | null
  request_id: string
  scored_at: string
  business_name: string | null
  owner_name: string | null
  business_type: string | null
  state: string | null
  requested_loan_amount: number | null
}

export interface CustomerProfileResponse {
  customer_id: string
  business_name: string
  owner_name: string | null
  business_type: string
  state: string | null
  years_in_operation: number | null
  requested_loan_amount: number | null
  is_blank_slate: boolean
  data_completeness: number
}

export interface DecisionRequest {
  customer_id: string
  decision: string
  remarks: string
}

export interface DecisionResponse {
  id: number
  customer_id: string
  decision: string
  remarks: string | null
  reviewer: string
  created_at: string
}

export interface Flags {
  is_blank_slate: boolean
  epfo_plausibility: EpfoPlausibilityFlag
  capacity_flag: CapacityFlag
  seasonality_flags: SeasonalityFlags
}

export interface EpfoPlausibilityFlag {
  flag: string
  message: string
  implied_wage: number | null
  employee_count: number | null
}

export interface CapacityFlag {
  flag: string
  message: string
  loan_to_revenue_ratio: number | null
  source: string
}

export interface SeasonalityFlags {
  fuel: SeasonalityFlag
  electricity: SeasonalityFlag
}

export interface SeasonalityFlag {
  flag: string
  message: string
  value: number | null
  expected_range: Record<string, number> | null
}

export interface ShapExplanation {
  shap_values: Record<string, number>
  base_value: number
  feature_ranking: FeatureRank[]
  human_readable_summary: string
}

export interface FeatureRank {
  feature_name: string
  value: number
  shap_value: number
  rank: number
  direction: string
  business_description: string
  source: string
}

export const CURATED_IDS = [
  { id: 'CUST00042', label: 'Ramesh Traders (blank, yes-to-go)' },
  { id: 'CUST00011', label: 'Shakti Mfg (full, disciplined)' },
  { id: 'CUST00087', label: 'Kaveri Logistics (blank, non-disciplined)' },
  { id: 'CUST00134', label: 'Anand Cold Chain (full, no-to-go)' },
]

export const BUCKET_COLORS: Record<string, { color: string; bg: string; border: string; label: string }> = {
  'yes-to-go':       { color: '#1B5FA8', bg: '#E6EEFA', border: '#A8C3ED', label: 'Yes-to-go' },
  'disciplined':     { color: '#1B6B3A', bg: '#E8F5EE', border: '#A8D5BA', label: 'Disciplined' },
  'non-disciplined': { color: '#B86B00', bg: '#FEF9ED', border: '#F5D98A', label: 'Non-disciplined' },
  'no-to-go':        { color: '#C41E3A', bg: '#FEE8EC', border: '#F0A8B0', label: 'No-to-go' },
}

export const FLAG_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  low_risk:    { bg: '#E8F5EE', color: '#1B6B3A', label: 'Low risk' },
  moderate:    { bg: '#FEF9ED', color: '#B86B00', label: 'Moderate' },
  high_risk:   { bg: '#FEE8EC', color: '#C41E3A', label: 'High risk' },
  unavailable: { bg: '#EDEDF2', color: '#54566B', label: 'Unavailable' },
  plausible:   { bg: '#E8F5EE', color: '#1B6B3A', label: 'Plausible' },
  flagged:     { bg: '#FEE8EC', color: '#C41E3A', label: 'Flagged' },
}
