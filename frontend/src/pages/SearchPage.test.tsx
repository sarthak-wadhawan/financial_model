import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, type SymbolSearchResult } from '../services/api'
import { SearchPage } from './SearchPage'

const result: SymbolSearchResult = { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', type: 'stock', source: 'test-fixture' }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><MemoryRouter><SearchPage /></MemoryRouter></QueryClientProvider>)
}
function enter(value = 'AAPL') { fireEvent.change(screen.getByRole('searchbox', { name: 'Symbol or company name' }), { target: { value } }) }
beforeEach(() => { vi.spyOn(api, 'searchSymbols').mockResolvedValue([result]) })
afterEach(() => vi.restoreAllMocks())

describe('SearchPage frozen symbol search contract', () => {
  it('renders accessible company search, not unimplemented news/event tabs', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Search Stocks' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Symbol or company name' })).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
  })
  it('shows coverage limits and avoids requesting an empty query', () => {
    mount()
    expect(screen.getByText(/Coverage depends on the connected provider/)).toBeInTheDocument()
    expect(api.searchSymbols).not.toHaveBeenCalled()
  })
  it('shows genuine debounce/loading state rather than only accepting input', async () => {
    vi.mocked(api.searchSymbols).mockImplementation(() => new Promise(() => {}))
    mount(); enter()
    expect(screen.getByRole('searchbox')).toHaveValue('AAPL')
    expect(await screen.findByText('Loading matching stocks…')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /AAPL/ })).not.toBeInTheDocument()
  })
  it('renders actual symbol, name, exchange and source from the array contract', async () => {
    mount(); enter()
    const link = await screen.findByRole('link', { name: /AAPL/ })
    expect(link).toHaveTextContent('Apple Inc.')
    expect(link).toHaveTextContent('NASDAQ')
    expect(link).toHaveTextContent('stock · Source: test-fixture')
    expect(screen.getByText('1 results')).toBeInTheDocument()
  })
  it('debounces rapid query changes and requests only the latest term', async () => {
    mount(); enter('AA'); enter('AAPL')
    await screen.findByRole('link', { name: /AAPL/ })
    expect(api.searchSymbols).toHaveBeenCalledTimes(1)
    expect(api.searchSymbols).toHaveBeenCalledWith('AAPL')
  })
  it('links the stock result to its research detail route', async () => {
    mount(); enter()
    expect(await screen.findByRole('link', { name: /AAPL/ })).toHaveAttribute('href', '/stocks/AAPL')
  })
  it('renders absent metadata honestly rather than assuming NASDAQ or a company', async () => {
    vi.mocked(api.searchSymbols).mockResolvedValue([{ ...result, name: null, exchange: null }])
    mount(); enter()
    const link = await screen.findByRole('link', { name: /AAPL/ })
    expect(link).toHaveTextContent('Company name unavailable')
    expect(link).toHaveTextContent('Exchange unavailable')
    expect(screen.queryByText('NASDAQ')).not.toBeInTheDocument()
  })
  it('distinguishes successful empty results from request failure', async () => {
    vi.mocked(api.searchSymbols).mockResolvedValue([])
    mount(); enter('ZZZZ')
    expect(await screen.findByText('No matching stocks available.')).toBeInTheDocument()
    expect(screen.getByText('0 results')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
  it('shows an explicit error and retries through the real query client', async () => {
    vi.mocked(api.searchSymbols).mockRejectedValueOnce(new Error('provider down')).mockResolvedValue([result])
    mount(); enter()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load matching stocks. Try again; this is not an empty result.')
    expect(screen.queryByText('No matching stocks available.')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }))
    expect(await screen.findByRole('link', { name: /AAPL/ })).toHaveAttribute('href', '/stocks/AAPL')
    expect(api.searchSymbols).toHaveBeenCalledTimes(2)
  })
  it('accepts single-character symbols supported by the frozen search contract', async () => {
    vi.mocked(api.searchSymbols).mockResolvedValue([{ ...result, symbol: 'F' }])
    mount(); enter('F')
    expect(await screen.findByRole('link', { name: /^F / })).toHaveAttribute('href', '/stocks/F')
    expect(api.searchSymbols).toHaveBeenCalledWith('F')
  })
  it('clearing a completed query removes stale results and makes no blank request', async () => {
    mount(); enter()
    await screen.findByRole('link', { name: /AAPL/ })
    enter(' ')
    await waitFor(() => expect(screen.getByText(/Coverage depends on the connected provider/)).toBeInTheDocument())
    expect(screen.queryByRole('link', { name: /AAPL/ })).not.toBeInTheDocument()
    expect(api.searchSymbols).toHaveBeenCalledTimes(1)
  })
})
