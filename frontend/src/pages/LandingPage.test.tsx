import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, type CompanyEvent, type MarketOverviewResponse } from '../services/api'
import { LandingPage } from './LandingPage'

const market: MarketOverviewResponse = { timestamp: '2026-10-14T15:00:00Z', snapshot_time: '2026-10-14T15:00:00Z', market_status: 'unknown', symbols_tracked: 2, market_data_status: 'available', quant_scanner_status: 'available', mode: 'demo', source: 'test-fixture', source_url: null, reason: null, indices: [{ symbol: 'SPY', price: 600, change: 0, change_pct: 0, market_timestamp: '2026-10-13T20:00:00Z', retrieved_at: '2026-10-14T15:00:00Z', source: 'test-fixture', price_kind: 'daily_close' }], top_gainers: [], top_losers: [], most_active: [] }
const event: CompanyEvent = { event_id: 'company-fixture', symbol: 'AAPL', event_type: 'sec_filing', title: 'Fixture company filing', description: null, scheduled_at: null, released_at: '2026-10-13T20:00:00Z', importance: 'high', status: 'released', source: 'test-fixture', source_url: 'https://www.sec.gov/Archives/', source_id: 'fixture-1', timezone: 'UTC', actual: null, forecast: null, previous: null, unit: null, first_seen_at: '2026-10-14T15:00:00Z', last_seen_at: '2026-10-14T15:00:00Z', created_at: '2026-10-14T15:00:00Z', updated_at: '2026-10-14T15:00:00Z', content_hash: 'fixture', metadata: {} }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><MemoryRouter><LandingPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: { sec: { status: 'not_refreshed', retrieved_at: null, reason: 'Unit test fixture; no source refresh requested' } } })
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-14T15:00:00Z'))
  vi.spyOn(api, 'getMarketOverview').mockResolvedValue(market)
  vi.spyOn(api, 'getMacroEvents').mockResolvedValue([])
  vi.spyOn(api, 'getQuantScannerTop').mockResolvedValue([])
  vi.spyOn(api, 'getRecentEvents').mockResolvedValue([])
  vi.spyOn(api, 'getWatchlists').mockResolvedValue([])
})
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

describe('LandingPage actual dashboard', () => {
  it('keeps market snapshot ahead of provider coverage in document order', async () => {
    mount()
    expect(await screen.findByText('600.00')).toBeInTheDocument()
    const sections = screen.getByRole('region', { name: 'Provider coverage' }).parentElement!.children
    expect(sections[1]).toHaveClass('market-overview')
    expect(sections[2]).toHaveAccessibleName('Provider coverage')
  })
  it('renders research purpose and human decision boundary', () => {
    mount()
    expect(screen.getByRole('heading', { level: 1, name: 'Your research dashboard' })).toBeInTheDocument()
    expect(screen.getByText(/You make the final decision/)).toBeInTheDocument()
  })
  it('provides actual research and scanner navigation', () => {
    mount()
    expect(screen.getByRole('link', { name: 'Search a company' })).toHaveAttribute('href', '/search')
    expect(screen.getByRole('link', { name: 'Explore scanner' })).toHaveAttribute('href', '/scanner')
  })
  it('renders provider daily close, zero change and distinct retrieval date', async () => {
    mount()
    expect(await screen.findByText('600.00')).toBeInTheDocument()
    expect(screen.getByText('0.00%')).toBeInTheDocument()
    expect(screen.getByText(/SPY — daily close, not a live quote/)).toBeInTheDocument()
    expect(screen.getByText(/Retrieval date \(not market time\): 2026-10-14/)).toBeInTheDocument()
    expect(screen.queryByText(/VIX|DXY/)).not.toBeInTheDocument()
  })
  it('groups macro releases separately from symbol-bearing company events', async () => {
    vi.mocked(api.getMacroEvents).mockResolvedValue([{ ...event, event_id: 'macro-fixture', symbol: null, title: 'Fixture macro release', event_type: 'cpi' }])
    vi.mocked(api.getRecentEvents).mockResolvedValue([event, { ...event, event_id: 'macro-recent', symbol: null, title: 'Not a company event' }])
    mount()
    expect(await screen.findByText('Fixture macro release')).toBeInTheDocument()
    const company = screen.getByRole('heading', { name: 'Recent company events' }).closest('section')!
    expect(await within(company).findByRole('link', { name: event.title })).toHaveAttribute('href', '/stocks/AAPL')
    expect(within(company).queryByText('Not a company event')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Just released — last 7 days' })).toBeInTheDocument()
  })
  it('shows independent unsupported instrument cards without hiding available SPY', async () => {
    vi.mocked(api.getMarketOverview).mockResolvedValue({ ...market, indices: [
      { ...market.indices[0], status: 'available' },
      ...['VIX', 'DXY', '10Y'].map(symbol => ({ symbol, status: 'unsupported', reason: `${symbol} is not supported; no proxy instrument is substituted`, price: null, change: null, change_pct: null, market_timestamp: null, retrieved_at: null, source: null, price_kind: null })),
    ] })
    mount()
    expect(await screen.findByText('600.00')).toBeInTheDocument()
    expect(within(screen.getByRole('group', { name: 'SPY instrument' })).getByText('Status: available')).toBeInTheDocument()
    for (const symbol of ['VIX', 'DXY', '10Y']) {
      const card = within(screen.getByRole('group', { name: `${symbol} instrument` }))
      expect(card.getByText('Status: unsupported')).toBeInTheDocument()
      expect(card.getByText(`${symbol} is not supported; no proxy instrument is substituted`)).toBeInTheDocument()
      expect(card.getByText(/Source: Unavailable/)).toBeInTheDocument()
      expect(card.queryByText('600.00')).not.toBeInTheDocument()
    }
  })
  it('renders a failed SPY instrument as provider_error rather than dropping its card', async () => {
    vi.mocked(api.getMarketOverview).mockResolvedValue({ ...market, market_data_status: 'provider_error', indices: [
      { ...market.indices[0], status: 'provider_error', reason: 'Market provider request failed', price: null, change: null, change_pct: null, market_timestamp: null },
    ] })
    mount()
    const card = within(await screen.findByRole('group', { name: 'SPY instrument' }))
    expect(card.getByText('Status: provider_error')).toBeInTheDocument()
    expect(card.getByText('Market provider request failed')).toBeInTheDocument()
    expect(card.queryByText('600.00')).not.toBeInTheDocument()
  })
  it('displays API candidate rank and component values without recalculating', async () => {
    vi.mocked(api.getQuantScannerTop).mockResolvedValue([{ symbol: 'AAPL', rank: 7, quant_score: 85, momentum_score: 0, trend_score: 90, liquidity_score: 80, volume_score: 70, volatility_quality_score: 60, price: 100, avg_dollar_volume_20d: 1e6, components: {}, calculated_at: '2026-10-14', market_timestamp: '2026-10-13', source: 'test-fixture', mode: 'demo' }])
    mount()
    const row = await screen.findByRole('row', { name: '#7 AAPL 85.0 0.0 90.0' })
    expect(within(row).getByRole('link', { name: 'AAPL' })).toHaveAttribute('href', '/stocks/AAPL')
    expect(api.getQuantScannerTop).toHaveBeenCalledWith(5)
  })
  it('labels fixture provenance and preserves unavailable publication dates', async () => {
    vi.mocked(api.getRecentEvents).mockResolvedValue([{ ...event, released_at: null }])
    mount()
    expect(await screen.findByText(/Publication date: Date unavailable · Source: test-fixture — test\/demo, not live/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View source' })).toHaveAttribute('href', event.source_url)
  })
  it('exposes honest failure independently of successful empty sections', async () => {
    vi.mocked(api.getMarketOverview).mockRejectedValue(new Error('provider down'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load market snapshot. Try again; this is not an empty result.')
    expect(await screen.findByText('No scanner candidates available.')).toBeInTheDocument()
    expect(screen.queryByText('No market snapshot available.')).not.toBeInTheDocument()
  })
  it('renders persistent watchlist summaries and navigation from the API', async () => {
    vi.mocked(api.getWatchlists).mockResolvedValue([{ id: 'fixture-list', name: 'Research list', description: null, sort_order: 'manual', is_default: true, item_count: 1, symbols: ['AAPL'], created_at: '2026-10-14', updated_at: '2026-10-14' }])
    mount()
    expect(await screen.findByRole('link', { name: 'Research list' })).toHaveAttribute('href', '/watchlists/fixture-list')
    expect(screen.getByText('1 symbols · Default')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage watchlists →' })).toHaveAttribute('href', '/watchlists')
  })
})
