import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { StockPage } from '../pages/StockPage'

describe('StockPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders stock header with symbol', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /AAPL/i })).toBeInTheDocument()
    expect(screen.getByText(/NASDAQ/i)).toBeInTheDocument()
  })

  it('renders all tab navigation buttons', () => {
    render(<StockPage />)
    const tabs = ['Overview', 'Earnings', 'Events', 'News', 'Insiders', 'Leadership', 'Filings', 'Quant']
    tabs.forEach(tab => {
      expect(screen.getByRole('tab', { name: tab })).toBeInTheDocument()
    })
  })

  it('shows overview tab by default', () => {
    render(<StockPage />)
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: /What You Need to Know/i })).toBeInTheDocument()
  })

  it('switches tabs when clicked', () => {
    render(<StockPage />)
    const earningsTab = screen.getByRole('tab', { name: 'Earnings' })
    fireEvent.click(earningsTab)
    expect(earningsTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: /Earnings/i })).toBeInTheDocument()
  })

  it('renders company impact and stock impact sections separately', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /Company Impact/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Stock Impact/i })).toBeInTheDocument()
  })

  it('renders scenario analysis with Base/Bull/Bear cases', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /Scenario Analysis/i })).toBeInTheDocument()
    expect(screen.getByText(/BASE CASE/i)).toBeInTheDocument()
    expect(screen.getByText(/BULL CASE/i)).toBeInTheDocument()
    expect(screen.getByText(/BEAR CASE/i)).toBeInTheDocument()
  })

  it('renders what would change the view section', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /What Would Change the View/i })).toBeInTheDocument()
  })

  it('renders confidence assessment', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /Confidence Assessment/i })).toBeInTheDocument()
    expect(screen.getByText(/75%/i)).toBeInTheDocument()
  })

  it('renders missing information', () => {
    render(<StockPage />)
    expect(screen.getByText(/Missing Information:/i)).toBeInTheDocument()
    expect(screen.getByText(/No recent earnings result available/i)).toBeInTheDocument()
  })

  it('renders supporting evidence section', () => {
    render(<StockPage />)
    expect(screen.getByRole('heading', { name: /Supporting Evidence/i })).toBeInTheDocument()
  })

  it('shows earnings tab when clicked', () => {
    render(<StockPage />)
    const earningsTab = screen.getByRole('tab', { name: 'Earnings' })
    fireEvent.click(earningsTab)
    expect(screen.getByRole('heading', { name: /Earnings/i })).toBeInTheDocument()
  })

  it('shows leadership tab with CEO/CFO', () => {
    render(<StockPage />)
    const leadershipTab = screen.getByRole('tab', { name: 'Leadership' })
    fireEvent.click(leadershipTab)
    expect(screen.getByText(/Tim Cook/i)).toBeInTheDocument()
    expect(screen.getByText(/Luca Maestri/i)).toBeInTheDocument()
  })

  it('shows quant tab with signals', () => {
    render(<StockPage />)
    const quantTab = screen.getByRole('tab', { name: 'Quant' })
    fireEvent.click(quantTab)
    expect(screen.getByRole('heading', { name: /Quant Signals/i })).toBeInTheDocument()
  })
})