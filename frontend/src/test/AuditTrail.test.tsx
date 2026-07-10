import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AuditTrail from '../components/AuditTrail'
import { MOCK_SCORE_RESPONSE, createMockFetch } from './mocks'

describe('AuditTrail', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders collapsed by default', () => {
    render(<AuditTrail customerId="CUST00042" />)
    expect(screen.getByText('Audit trail')).toBeInTheDocument()
    expect(screen.queryByText('Scored at')).not.toBeInTheDocument()
  })

  it('loads and displays entries on toggle', async () => {
    globalThis.fetch = createMockFetch([MOCK_SCORE_RESPONSE])
    render(<AuditTrail customerId="CUST00042" />)
    fireEvent.click(screen.getByText('Audit trail'))

    await waitFor(() => {
      expect(screen.getByText('disciplined')).toBeInTheDocument()
    })
    expect(screen.getByText('live')).toBeInTheDocument()
    expect(screen.getByText('85.0%')).toBeInTheDocument()
  })

  it('shows loading state', async () => {
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}))
    render(<AuditTrail customerId="CUST00042" />)
    fireEvent.click(screen.getByText('Audit trail'))
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows error message on fetch failure', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
      text: () => Promise.resolve('Internal Server Error'),
    })
    render(<AuditTrail customerId="CUST00042" />)
    fireEvent.click(screen.getByText('Audit trail'))

    await waitFor(() => {
      expect(screen.getByText(/Internal Server Error/)).toBeInTheDocument()
    })
  })

  it('shows empty state', async () => {
    globalThis.fetch = createMockFetch([])
    render(<AuditTrail customerId="CUST00042" />)
    fireEvent.click(screen.getByText('Audit trail'))

    await waitFor(() => {
      expect(screen.getByText('No previous scores recorded.')).toBeInTheDocument()
    })
  })
})
