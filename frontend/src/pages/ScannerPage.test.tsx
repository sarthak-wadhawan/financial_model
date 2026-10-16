import { act, render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, type MarketOverviewResponse, type QuantCandidate } from '../services/api'
import { ScannerPage } from './ScannerPage'

const candidate: QuantCandidate = { symbol: 'AAPL', rank: 7, quant_score: 85, momentum_score: 0, trend_score: 90, liquidity_score: 80, volume_score: 70, volatility_quality_score: 60, price: 0, avg_dollar_volume_20d: 1e6, components: {}, calculated_at: '2026-10-14', market_timestamp: '2026-10-13', source: 'test-fixture', mode: 'demo' }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><MemoryRouter><ScannerPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.spyOn(api, 'getQuantScannerTop').mockResolvedValue([candidate])
  vi.spyOn(api, 'getMarketOverview').mockResolvedValue({ timestamp: '2026-10-14', snapshot_time: '2026-10-14', mode: 'demo', source: 'test-fixture', source_url: null, reason: null, market_data_status: 'available', quant_scanner_status: 'available', market_status: 'unknown', symbols_tracked: 2, indices: [], top_gainers: [], top_losers: [], most_active: [] } satisfies MarketOverviewResponse)
  vi.spyOn(api, 'getScannerStatus').mockResolvedValue({ status: 'available', reason: null, mode: 'demo', source: 'test-fixture', calculated_at: '2026-10-14', market_timestamp: '2026-10-13', universe_size: 2 })
})
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

describe('ScannerPage actual provider rankings', () => {
  it('renders deterministic research purpose and labelled result selector', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Quant Scanner' })).toBeInTheDocument()
    expect(screen.getByText(/not price forecasts or trade recommendations/)).toBeInTheDocument()
    expect(screen.getByLabelText('Results')).toHaveValue('20')
    for (const n of [10, 20, 50, 100]) expect(screen.getByRole('option', { name: `Top ${n}`, exact: true })).toBeInTheDocument()
  })
  it('shows actual market status and distinct scanner timestamps/source', async () => {
    mount()
    expect(await screen.findByText('unknown')).toBeInTheDocument()
    expect(screen.getByText('Symbols tracked').parentElement).toHaveTextContent('2')
    expect(await screen.findByText(/Source: test-fixture · Market date: 2026-10-13/)).toBeInTheDocument()
    expect(screen.getByText('Calculation date').parentElement).toHaveTextContent('2026-10-14')
  })
  it('renders exact component headers and backend rank/zero values', async () => {
    mount()
    await screen.findByText('#7')
    for (const name of ['Rank', 'Symbol', 'Quant Score', 'Momentum', 'Trend', 'Liquidity', 'Volume', 'Vol Quality', 'Price']) expect(screen.getByRole('columnheader', { name })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: '#7 AAPL 85.0 0.0 90.0 80.0 70.0 60.0 $0.00' })).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
  })
  it('requests selected top N from the backend, not a client-side rescore', async () => {
    mount()
    await screen.findByText('#7')
    fireEvent.change(screen.getByLabelText('Results'), { target: { value: '50' } })
    await waitFor(() => expect(api.getQuantScannerTop).toHaveBeenCalledWith(50))
    expect(screen.getByLabelText('Results')).toHaveValue('50')
    expect(await screen.findByText('#7')).toBeInTheDocument()
  })
  it('links candidate symbol to its stock research page', async () => {
    mount()
    expect(await screen.findByRole('link', { name: 'AAPL' })).toHaveAttribute('href', '/stocks/AAPL')
  })
  it('filters only returned symbols while retaining backend rank and scores', async () => {
    vi.mocked(api.getQuantScannerTop).mockResolvedValue([candidate, { ...candidate, symbol: 'MSFT', rank: 12, quant_score: 50 }])
    mount()
    await screen.findByText('#12')
    fireEvent.change(screen.getByLabelText('Filter returned symbols'), { target: { value: ' aapl ' } })
    expect(screen.queryByRole('link', { name: 'MSFT' })).not.toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /#7 AAPL/ })).getByText('85.0')).toBeInTheDocument()
    expect(api.getQuantScannerTop).toHaveBeenCalledTimes(1)
  })
  it('distinguishes provider failure from successfully empty candidates', async () => {
    vi.mocked(api.getQuantScannerTop).mockRejectedValue(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load scanner candidates from the connected provider')
    expect(screen.queryByText(/No scanner candidates/)).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
  it('does not claim operational scanning for unavailable/empty data', async () => {
    vi.mocked(api.getQuantScannerTop).mockResolvedValue([])
    vi.mocked(api.getScannerStatus).mockResolvedValue({ status: 'unavailable', reason: 'Provider not configured', source: 'Alpaca/IEX', mode: 'real', calculated_at: null, universe_size: 0 })
    mount()
    expect(await screen.findByText(/Provider not configured/)).toBeInTheDocument()
    expect(await screen.findByText('No scanner candidates from the connected provider available.')).toBeInTheDocument()
  })

  it('waits for populated scan completion before reading previously unrun status', async () => {
    let complete!: (data: QuantCandidate[]) => void
    let ran = false
    vi.mocked(api.getQuantScannerTop).mockImplementation(() => new Promise(resolve => { complete = data => { ran = true; resolve(data) } }))
    vi.mocked(api.getScannerStatus).mockImplementation(async () => ({ status: ran ? 'available' : 'unavailable', reason: ran ? null : 'Scanner has not run', source: 'test-fixture', mode: 'demo', calculated_at: ran ? '2026-10-14' : null, market_timestamp: ran ? '2026-10-13' : null, universe_size: 2 }))
    mount()
    expect(api.getScannerStatus).not.toHaveBeenCalled()
    await act(async () => { complete([candidate]) })
    expect(await screen.findByText(/Status: available.*Market date: 2026-10-13/)).toBeInTheDocument()
    expect(screen.queryByText(/Scanner has not run/)).not.toBeInTheDocument()
    expect(api.getScannerStatus).toHaveBeenCalledTimes(1)
  })

  it('refreshes status after Refresh results and rejects a late older status response', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-10-15T12:00:00Z'))
    let oldStatus!: (value: Awaited<ReturnType<typeof api.getScannerStatus>>) => void
    vi.mocked(api.getScannerStatus).mockImplementationOnce(() => new Promise(resolve => { oldStatus = resolve }))
      .mockResolvedValue({ status: 'available', reason: null, source: 'test-fixture', mode: 'demo', calculated_at: '2026-10-15', market_timestamp: '2026-10-14', universe_size: 2 })
    mount()
    await waitFor(() => expect(api.getScannerStatus).toHaveBeenCalledTimes(1))
    vi.setSystemTime(new Date('2026-10-15T12:01:00Z'))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh results' }))
    expect(await screen.findByText(/Status: available.*Market date: 2026-10-14/)).toBeInTheDocument()
    expect(api.getQuantScannerTop).toHaveBeenCalledTimes(2)
    expect(api.getScannerStatus).toHaveBeenCalledTimes(2)
    await act(async () => { oldStatus({ status: 'unavailable', reason: 'Scanner has not run', source: 'test-fixture', mode: 'demo', calculated_at: null, universe_size: 2 }) })
    expect(screen.queryByText(/Scanner has not run/)).not.toBeInTheDocument()
    expect(screen.getByText(/Status: available.*Market date: 2026-10-14/)).toBeInTheDocument()
  })
})
