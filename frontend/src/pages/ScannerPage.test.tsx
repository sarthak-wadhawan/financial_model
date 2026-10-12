import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ScannerPage } from '../pages/ScannerPage'

describe('ScannerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title and subtitle', () => {
    render(<ScannerPage />)
    expect(screen.getByRole('heading', { name: /Quant Scanner/i })).toBeInTheDocument()
    expect(screen.getByText(/Top ranked stocks by deterministic quant signals/i)).toBeInTheDocument()
  })

  it('renders top N selector', () => {
    render(<ScannerPage />)
    expect(screen.getByLabelText(/Number of results/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Top 10/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Top 20/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Top 50/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Top 100/i })).toBeInTheDocument()
  })

  it('renders scanner stats', () => {
    render(<ScannerPage />)
    expect(screen.getByText(/Market Status/i)).toBeInTheDocument()
    expect(screen.getByText(/Symbols Tracked/i)).toBeInTheDocument()
    expect(screen.getByText(/As of/i)).toBeInTheDocument()
  })

  it('renders scanner table with correct headers', () => {
    render(<ScannerPage />)
    const headers = ['Rank', 'Symbol', 'Score', 'Momentum', 'Trend', 'Liquidity', 'Volume', 'Vol Quality']
    headers.forEach(header => {
      expect(screen.getByRole('columnheader', { name: header })).toBeInTheDocument()
    })
  })

  it('renders candidate rows when data loads', () => {
    render(<ScannerPage />)
    expect(screen.getByText(/AAPL/i)).toBeInTheDocument()
    expect(screen.getByText(/85/i)).toBeInTheDocument()
    expect(screen.getByText(/#1/i)).toBeInTheDocument()
  })

  it('updates top N when selector changes', () => {
    render(<ScannerPage />)
    const select = screen.getByLabelText(/Number of results/i)
    fireEvent.change(select, { target: { value: '50' } })
    expect(select).toHaveValue('50')
  })

  it('links symbol to stock page', () => {
    render(<ScannerPage />)
    const link = screen.getByRole('link', { name: /AAPL/i })
    expect(link).toHaveAttribute('href', '/stocks/AAPL')
  })
})