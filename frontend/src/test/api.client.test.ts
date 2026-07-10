import { describe, it, expect, beforeEach } from 'vitest'
import { fetchScore, fetchAudit, fetchCustomerProfile, fetchDecisions, fetchPendingReviews, submitDecision, ApiError, NotFoundError, ServiceDegradedError } from '../api/client'
import { MOCK_SCORE_RESPONSE, createMockFetch } from './mocks'

describe('API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('fetchScore', () => {
    it('should return score response on success', async () => {
      globalThis.fetch = createMockFetch(MOCK_SCORE_RESPONSE)
      const result = await fetchScore('CUST00042')
      expect(result.customerId).toBe('CUST00042')
      expect(result.bucket).toBe('disciplined')
    })

    it('should throw NotFoundError on 404', async () => {
      globalThis.fetch = createMockFetch({}, 404)
      await expect(fetchScore('UNKNOWN')).rejects.toThrow(NotFoundError)
    })

    it('should throw ServiceDegradedError on 503', async () => {
      globalThis.fetch = createMockFetch({}, 503)
      await expect(fetchScore('CUST00001')).rejects.toThrow(ServiceDegradedError)
    })

    it('should throw ApiError on other errors', async () => {
      globalThis.fetch = createMockFetch({}, 500)
      await expect(fetchScore('CUST00001')).rejects.toThrow(ApiError)
    })
  })

  describe('fetchAudit', () => {
    it('should return audit list', async () => {
      globalThis.fetch = createMockFetch([MOCK_SCORE_RESPONSE])
      const result = await fetchAudit('CUST00042')
      expect(Array.isArray(result)).toBe(true)
      expect(result[0].customerId).toBe('CUST00042')
    })

    it('should throw ApiError on failure', async () => {
      globalThis.fetch = createMockFetch({}, 500)
      await expect(fetchAudit('CUST00001')).rejects.toThrow(ApiError)
    })
  })

  describe('fetchCustomerProfile', () => {
    it('should return profile response', async () => {
      const profile = { customer_id: 'CUST00001', business_name: 'Test', business_type: 'retail', is_blank_slate: false, data_completeness: 0.8 }
      globalThis.fetch = createMockFetch(profile)
      const result = await fetchCustomerProfile('CUST00001')
      expect(result.customer_id).toBe('CUST00001')
    })

    it('should throw NotFoundError on 404', async () => {
      globalThis.fetch = createMockFetch({}, 404)
      await expect(fetchCustomerProfile('UNKNOWN')).rejects.toThrow(NotFoundError)
    })
  })

  describe('submitDecision', () => {
    it('should post decision and return response', async () => {
      const resp = { id: 1, customer_id: 'CUST00001', decision: 'APPROVE', remarks: 'OK', reviewer: 'uw', created_at: new Date().toISOString() }
      globalThis.fetch = createMockFetch(resp)
      const result = await submitDecision({ customer_id: 'CUST00001', decision: 'APPROVE', remarks: 'OK' })
      expect(result.decision).toBe('APPROVE')
    })

    it('should throw ApiError on failure', async () => {
      globalThis.fetch = createMockFetch({}, 400)
      await expect(submitDecision({ customer_id: 'CUST00001', decision: 'BAD', remarks: '' })).rejects.toThrow(ApiError)
    })
  })

  describe('fetchDecisions', () => {
    it('should return decisions list', async () => {
      globalThis.fetch = createMockFetch([{ id: 1, decision: 'APPROVE' }])
      const result = await fetchDecisions('CUST00001')
      expect(result.length).toBe(1)
    })
  })

  describe('fetchPendingReviews', () => {
    it('should return pending reviews', async () => {
      globalThis.fetch = createMockFetch([{ id: 1, decision: 'REVIEW' }])
      const result = await fetchPendingReviews()
      expect(result.length).toBe(1)
    })
  })
})
