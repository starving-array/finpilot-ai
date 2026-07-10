import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from '../App'
import { MOCK_SCORE_RESPONSE } from './mocks'

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the search bar', () => {
    render(<App />)
    expect(screen.getByPlaceholderText('e.g. CUST00042')).toBeInTheDocument()
  })

  it('renders idle state by default', () => {
    render(<App />)
    expect(screen.getByText('No customer loaded')).toBeInTheDocument()
  })

  it('shows loading state when searching', async () => {
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}))
    render(<App />)

    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'CUST00001' } })
    fireEvent.click(screen.getByText('Fetch score'))

    expect(await screen.findByText(/Scoring customer/)).toBeInTheDocument()
  })

  it('shows results on successful fetch', async () => {
    globalThis.fetch = createMockFetch(MOCK_SCORE_RESPONSE)
    render(<App />)

    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'CUST00042' } })
    fireEvent.click(screen.getByText('Fetch score'))

    await waitFor(() => {
      expect(screen.getByText('Ramesh Traders')).toBeInTheDocument()
    })
    expect(screen.getByText('Disciplined')).toBeInTheDocument()
  })

  it('shows not found state', async () => {
    globalThis.fetch = createMockFetch({}, 404)
    render(<App />)

    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'UNKNOWN' } })
    fireEvent.click(screen.getByText('Fetch score'))

    await waitFor(() => {
      expect(screen.getByText(/No profile found/)).toBeInTheDocument()
    })
  })

  it('shows service degraded state', async () => {
    globalThis.fetch = createMockFetch({}, 503)
    render(<App />)

    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'CUST00001' } })
    fireEvent.click(screen.getByText('Fetch score'))

    await waitFor(() => {
      expect(screen.getByText('Service Unavailable')).toBeInTheDocument()
    })
  })

  it('shows stale banner when source is cache-fallback', async () => {
    const staleResult = { ...MOCK_SCORE_RESPONSE, source: 'cache-fallback', stale_since: new Date(Date.now() - 7200000).toISOString() }
    globalThis.fetch = createMockFetch(staleResult)
    render(<App />)

    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'CUST00042' } })
    fireEvent.click(screen.getByText('Fetch score'))

    await waitFor(() => {
      expect(screen.getByText(/cached result/)).toBeInTheDocument()
    })
  })
})

function createMockFetch(data: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  })
}
