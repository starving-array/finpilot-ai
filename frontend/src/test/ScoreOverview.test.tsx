import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreOverview from '../components/ScoreOverview'
import { MOCK_SCORE_RESPONSE } from './mocks'

describe('ScoreOverview', () => {
  it('renders customer name', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('Ramesh Traders')).toBeInTheDocument()
  })

  it('renders customer ID and business type', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText(/CUST00042/)).toBeInTheDocument()
    expect(screen.getAllByText(/retail/).length).toBeGreaterThanOrEqual(1)
  })

  it('renders the bucket label', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('Disciplined')).toBeInTheDocument()
  })

  it('renders score value', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('78')).toBeInTheDocument()
  })

  it('renders model confidence', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('renders blank-slate badge when applicable', () => {
    const blankResult = { ...MOCK_SCORE_RESPONSE, flags: { ...MOCK_SCORE_RESPONSE.flags, is_blank_slate: true } }
    render(<ScoreOverview result={blankResult} />)
    expect(screen.getByText('Blank-slate applicant')).toBeInTheDocument()
  })

  it('renders key factors', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('Payment regularity')).toBeInTheDocument()
    expect(screen.getByText('Financial capacity')).toBeInTheDocument()
    expect(screen.getByText('Business longevity')).toBeInTheDocument()
    expect(screen.getByText('Data coverage')).toBeInTheDocument()
    expect(screen.getByText('Evidence confidence')).toBeInTheDocument()
  })

  it('renders flag badges', () => {
    render(<ScoreOverview result={MOCK_SCORE_RESPONSE} />)
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
    expect(screen.getByText('Plausible')).toBeInTheDocument()
  })
})
