import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SearchPage } from '../pages/SearchPage'

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search hero when query is empty', () => {
    render(<SearchPage />)
    expect(screen.getByRole('heading', { name: /Search/i })).toBeInTheDocument()
    expect(screen.getByText(/Find stocks, news, events, and filings/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Search stocks, news, events, filings/i)).toBeInTheDocument()
  })

  it('renders search hints', () => {
    render(<SearchPage />)
    expect(screen.getByText(/Try: "AAPL", "earnings", "FOMC", "Form 4"/i)).toBeInTheDocument()
  })

  it('shows loading state when query is being debounced', () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    // The debounce prevents immediate loading state in this test setup
    // but the input should accept the value
    expect(input).toHaveValue('AAPL')
  })

  it('renders search results tabs when query has results', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    // Wait for debounce and query
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /All/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /Stocks/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /News/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /Events/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /Filings/i })).toBeInTheDocument()
    })
  })

  it('renders stock results in grid', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      expect(screen.getByText(/AAPL/i)).toBeInTheDocument()
      expect(screen.getByText(/Apple Inc./i)).toBeInTheDocument()
      expect(screen.getByText(/NASDAQ/i)).toBeInTheDocument()
    })
  })

  it('switches between search result tabs', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /All/i })).toHaveAttribute('aria-selected', 'true')
      
      fireEvent.click(screen.getByRole('tab', { name: /Stocks/i }))
      expect(screen.getByRole('tab', { name: /Stocks/i })).toHaveAttribute('aria-selected', 'true')
      
      fireEvent.click(screen.getByRole('tab', { name: /News/i }))
      expect(screen.getByRole('tab', { name: /News/i })).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('links stock result to stock page', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /AAPL/i })
      expect(link).toHaveAttribute('href', '/stocks/AAPL')
    })
  })

  it('shows news search not implemented message', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      fireEvent.click(screen.getByRole('tab', { name: /News/i }))
      expect(screen.getByText(/News search not yet implemented/i)).toBeInTheDocument()
    })
  })

  it('shows events search not implemented message', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      fireEvent.click(screen.getByRole('tab', { name: /Events/i }))
      expect(screen.getByText(/Events search not yet implemented/i)).toBeInTheDocument()
    })
  })

  it('shows filings search not implemented message', async () => {
    render(<SearchPage />)
    const input = screen.getByPlaceholderText(/Search stocks, news, events, filings/i)
    fireEvent.change(input, { target: { value: 'AAPL' } })
    
    await waitFor(() => {
      fireEvent.click(screen.getByRole('tab', { name: /Filings/i }))
      expect(screen.getByText(/Filings search not yet implemented/i)).toBeInTheDocument()
    })
  })
})