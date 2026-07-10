import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Layout from '../components/Layout'

describe('Layout', () => {
  const defaultProps = {
    activeTab: 'Score lookup',
    onTabChange: vi.fn(),
    onClear: vi.fn(),
    children: <div data-testid="child">Content</div>,
  }

  it('renders navigation tabs', () => {
    render(<Layout {...defaultProps} />)
    expect(screen.getByText('Score lookup')).toBeInTheDocument()
    expect(screen.getByText('Audit log')).toBeInTheDocument()
    expect(screen.getByText('Pending review')).toBeInTheDocument()
    expect(screen.getByText('Reports')).toBeInTheDocument()
  })

  it('renders header elements', () => {
    render(<Layout {...defaultProps} />)
    expect(screen.getByText('IDBI Bank')).toBeInTheDocument()
    expect(screen.getByText('Underwriter Console')).toBeInTheDocument()
    expect(screen.getByText('AI-Assisted Scoring')).toBeInTheDocument()
  })

  it('renders children content', () => {
    render(<Layout {...defaultProps} />)
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('calls onTabChange when a tab is clicked', () => {
    const onTabChange = vi.fn()
    render(<Layout {...defaultProps} onTabChange={onTabChange} />)
    fireEvent.click(screen.getByText('Audit log'))
    expect(onTabChange).toHaveBeenCalledWith('Audit log')
  })

  it('highlights active tab', () => {
    render(<Layout {...defaultProps} activeTab="Audit log" />)
    const activeTab = screen.getByText('Audit log')
    expect(activeTab).toHaveStyle({ borderBottom: '2.5px solid #C8A951' })
  })

  it('calls onClear when non-score tab is clicked', () => {
    const onClear = vi.fn()
    render(<Layout {...defaultProps} onClear={onClear} />)
    fireEvent.click(screen.getByText('Audit log'))
    expect(onClear).toHaveBeenCalledOnce()
  })
})
