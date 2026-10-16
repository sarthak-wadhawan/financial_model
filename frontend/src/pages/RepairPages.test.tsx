import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from '../services/api'
import type { Interpretation } from '../services/api'
import { LandingPage } from './LandingPage'
import { ScannerPage } from './ScannerPage'
import { StockPage } from './StockPage'

function renderPage(page: React.ReactNode, route = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><Routes><Route path={route.includes('/stocks/') ? '/stocks/:symbol' : '/'} element={page} /></Routes></MemoryRouter></QueryClientProvider>)
}
afterEach(() => vi.restoreAllMocks())
beforeEach(() => { vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: {} }) })

describe('repair research pages', () => {
  it('isolates dashboard failures and never calls them empty data', async () => {
    vi.spyOn(api, 'getMarketOverview').mockRejectedValue(new Error('offline'))
    vi.spyOn(api, 'getMacroEvents').mockResolvedValue([])
    vi.spyOn(api, 'getQuantScannerTop').mockResolvedValue([])
    vi.spyOn(api, 'getRecentEvents').mockResolvedValue([])
    vi.spyOn(api, 'getWatchlists').mockResolvedValue([])
    renderPage(<LandingPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load market snapshot')
    expect(await screen.findByText('No macro events available.')).toBeInTheDocument()
    expect(screen.queryByText('No market snapshot available.')).not.toBeInTheDocument()
  })
  it('keeps backend ranks and zero component values while filtering', async () => {
    vi.spyOn(api, 'getMarketOverview').mockRejectedValue(new Error('offline'))
    vi.spyOn(api, 'getScannerStatus').mockResolvedValue({ status: 'available', reason: null, mode: 'demo', source: 'mock', calculated_at: '2026-10-14', universe_size: 3 })
    vi.spyOn(api, 'getQuantScannerTop').mockResolvedValue([{ symbol: 'AAPL', rank: 7, quant_score: 0, momentum_score: 0, trend_score: 1, liquidity_score: 2, volume_score: 3, volatility_quality_score: 4, price: 0, avg_dollar_volume_20d: 0, components: {}, calculated_at: '2026-10-14', market_timestamp: '2026-10-13', source: 'mock', mode: 'demo' }])
    renderPage(<ScannerPage />)
    expect(await screen.findByText('#7')).toBeInTheDocument()
    expect(screen.getAllByText('0.0')).toHaveLength(2)
    expect(screen.getByText('$0.00')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Filter returned symbols'), { target: { value: 'MSFT' } })
    expect(screen.getByText('No returned symbols match this filter.')).toBeInTheDocument()
  })
  it('keeps impacts separate, renders conditions and does not invent probabilities or prices', async () => {
    vi.spyOn(api, 'getStockDetail').mockRejectedValue(new Error('offline'))
    vi.spyOn(api, 'getBars').mockResolvedValue({ symbol: 'AAPL', timeframe: '1Day', bars: [{ t: '2026-10-12', o: 0, h: 0, l: 0, c: 0, v: 0 }, { t: '2026-10-13', o: 2, h: 2, l: 2, c: 2, v: 10 }], status: 'available', reason: null, source: 'mock', mode: 'demo' })
    const impact = { direction: 'unknown', magnitude: 'unknown', horizon: 'unknown', confidence: 0, reasons: [] }
    const scenario = { description: 'Insufficient evidence', probability_band: null, required_conditions: ['Verify a primary release'] }
    const interpretation: Interpretation = { interpretation_id: 'test', symbol: 'AAPL', as_of: '2026-10-14', headline: 'Evidence unavailable', what_happened: 'No supported event', what_it_means: 'Unknown', why_it_matters: 'Avoid unsupported conclusions', company_impact: impact, stock_impact: { bias: 'unknown', magnitude: 'unknown', horizon: 'unknown', confidence: 0, reasons: [] }, base_case: scenario, bull_case: scenario, bear_case: scenario, what_would_change_view: [], confidence: 0, confidence_reasons: [], missing_information: ['No primary release'], supporting_evidence: [], generated_at: '2026-10-14', engine_version: 'test' }
    vi.spyOn(api, 'getInterpretation').mockResolvedValue(interpretation)
    vi.spyOn(api, 'getEarnings').mockResolvedValue([])
    renderPage(<StockPage />, '/stocks/AAPL')
    expect(await screen.findByRole('heading', { name: 'Company Impact' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Stock Impact' })).toBeInTheDocument()
    expect(screen.getByText('Price unavailable')).toBeInTheDocument()
    expect(screen.queryByText('NASDAQ')).not.toBeInTheDocument()
    expect(screen.queryByText(/Backend probability band/)).not.toBeInTheDocument()
    expect(screen.getAllByText('Verify a primary release')).toHaveLength(3)
    fireEvent.click(screen.getByText('Price history — provider bars'))
    expect(await screen.findByRole('img', { name: 'Provider-supplied daily closing price history' })).toBeInTheDocument()
    expect(screen.getByText(/Range \$0.00–\$2.00/)).toBeInTheDocument()
    expect(screen.getByText(/Mode: demo · Source: mock/)).toBeInTheDocument()
    const overview = screen.getByRole('tab', { name: 'Overview' })
    fireEvent.keyDown(overview, { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Earnings' })).toHaveFocus()
    expect(screen.getByRole('tab', { name: 'Earnings' })).toHaveAttribute('aria-selected', 'true')
  })
})
