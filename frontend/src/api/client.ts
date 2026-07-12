import type { ScoreResponse, CustomerProfileResponse, DecisionRequest, DecisionResponse } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export async function fetchScore(customerId: string, enableSeasonality?: boolean, referenceMonth?: number): Promise<ScoreResponse> {
  const params = new URLSearchParams()
  if (enableSeasonality) params.set('enableSeasonality', 'true')
  if (referenceMonth != null) params.set('referenceMonth', String(referenceMonth))
  const qs = params.toString()
  const url = qs ? `${BASE_URL}/score/${customerId}?${qs}` : `${BASE_URL}/score/${customerId}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    if (res.status === 404) throw new NotFoundError()
    if (res.status === 503) throw new ServiceDegradedError()
    throw new ApiError(res.status, await res.text())
  }
  return res.json()
}

export async function fetchAudit(customerId: string): Promise<ScoreResponse[]> {
  const res = await fetch(`${BASE_URL}/score/audit/${customerId}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json()
}

export async function fetchCustomerProfile(customerId: string): Promise<CustomerProfileResponse> {
  const res = await fetch(`${BASE_URL}/customers/${customerId}/profile`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    if (res.status === 404) throw new NotFoundError()
    throw new ApiError(res.status, await res.text())
  }
  return res.json()
}

export async function submitDecision(req: DecisionRequest): Promise<DecisionResponse> {
  const res = await fetch(`${BASE_URL}/decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json()
}

export async function fetchDecisions(customerId: string): Promise<DecisionResponse[]> {
  const res = await fetch(`${BASE_URL}/decisions/${customerId}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json()
}

export async function fetchPendingReviews(): Promise<DecisionResponse[]> {
  const res = await fetch(`${BASE_URL}/decisions/pending`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json()
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export class NotFoundError extends Error {
  constructor() {
    super('Customer not found')
    this.name = 'NotFoundError'
  }
}

export class ServiceDegradedError extends Error {
  constructor() {
    super('Scoring service is temporarily unavailable')
    this.name = 'ServiceDegradedError'
  }
}
