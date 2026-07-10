import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SearchBar from '../components/SearchBar'

describe('SearchBar', () => {
  const defaultProps = {
    customerId: '',
    onCustomerIdChange: vi.fn(),
    businessType: '',
    onBusinessTypeChange: vi.fn(),
    onFetch: vi.fn(),
    onClear: vi.fn(),
    disabled: false,
  }

  it('renders input field and buttons', () => {
    render(<SearchBar {...defaultProps} />)
    expect(screen.getByPlaceholderText('e.g. CUST00042')).toBeInTheDocument()
    expect(screen.getByText('Fetch score')).toBeInTheDocument()
    expect(screen.getByText('Clear')).toBeInTheDocument()
  })

  it('calls onFetch when Fetch score is clicked', () => {
    const onFetch = vi.fn()
    render(<SearchBar {...defaultProps} customerId="CUST00001" onFetch={onFetch} />)
    fireEvent.click(screen.getByText('Fetch score'))
    expect(onFetch).toHaveBeenCalledOnce()
  })

  it('disables Fetch button when customerId is empty', () => {
    render(<SearchBar {...defaultProps} />)
    expect(screen.getByText('Fetch score')).toBeDisabled()
  })

  it('disables Fetch button when disabled prop is true', () => {
    render(<SearchBar {...defaultProps} customerId="CUST00001" disabled={true} />)
    expect(screen.getByText('Fetch score')).toBeDisabled()
  })

  it('calls onCustomerIdChange when input changes', () => {
    const onChange = vi.fn()
    render(<SearchBar {...defaultProps} onCustomerIdChange={onChange} />)
    fireEvent.change(screen.getByPlaceholderText('e.g. CUST00042'), { target: { value: 'CUST001' } })
    expect(onChange).toHaveBeenCalledWith('CUST001')
  })

  it('calls onFetch on Enter key', () => {
    const onFetch = vi.fn()
    render(<SearchBar {...defaultProps} customerId="CUST00001" onFetch={onFetch} />)
    fireEvent.keyDown(screen.getByPlaceholderText('e.g. CUST00042'), { key: 'Enter' })
    expect(onFetch).toHaveBeenCalledOnce()
  })

  it('calls onClear when Clear button is clicked', () => {
    const onClear = vi.fn()
    render(<SearchBar {...defaultProps} onClear={onClear} />)
    fireEvent.click(screen.getByText('Clear'))
    expect(onClear).toHaveBeenCalledOnce()
  })

  it('renders demo profile buttons', () => {
    render(<SearchBar {...defaultProps} />)
    expect(screen.getByText('CUST00042')).toBeInTheDocument()
    expect(screen.getByText('CUST00011')).toBeInTheDocument()
  })
})
