import { render, screen, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, type Interpretation, type CompanyEvent, type QuantSignals, type StockDetail } from '../services/api'
import { StockPage } from './StockPage'

const scenario = { description: 'Base fixture scenario', probability_band: null, required_conditions: ['Verify primary release'] }
const interpretation: Interpretation = { interpretation_id: 'fixture', symbol: 'AAPL', as_of: '2026-10-14', headline: 'Fixture headline', what_happened: 'An evidence-backed filing', what_it_means: 'Company fundamentals changed', why_it_matters: 'Stock response may differ', company_impact: { direction: 'positive', magnitude: 'moderate', horizon: 'medium_term', confidence: 0.75, reasons: ['Company fixture reason'] }, stock_impact: { bias: 'mixed', magnitude: 'low', horizon: 'short_term', confidence: 0.5, reasons: ['Stock fixture reason'] }, base_case: scenario, bull_case: { ...scenario, description: 'Bull fixture scenario' }, bear_case: { ...scenario, description: 'Bear fixture scenario' }, what_would_change_view: [{ trigger: 'Primary release', description: 'Verify a new official statement' }], confidence: 0.75, confidence_reasons: ['Primary source'], missing_information: ['No recent earnings result available'], supporting_evidence: [{ evidence_id: 'fixture-evidence', source_type: 'SEC', description: 'Primary filing evidence', url: 'https://www.sec.gov/Archives/', timestamp: '2026-10-13T20:00:00Z' }], generated_at: '2026-10-14', engine_version: 'test-fixture' }
const quant: QuantSignals = { symbol: 'AAPL', quant_score: 0, rank: 7, universe_size: 20, components: { momentum: 0 }, signals: { momentum_20d: 0 }, status: 'available', reason: null, mode: 'demo', source: 'test-fixture', calculated_at: '2026-10-14' }
const stock: StockDetail = { symbol: 'AAPL', name: 'Apple fixture', exchange: 'NASDAQ', price: 0, change: 0, change_pct: 0, volume: 0, market_cap: null, pe_ratio: null, dividend_yield: null, price_data: { status: 'available', reason: null, mode: 'demo', source: 'test-fixture', price_kind: 'daily_close', market_timestamp: '2026-10-13T20:00:00Z', retrieved_at: '2026-10-14T15:00:00Z' }, quant_signals: quant, interpretation, events: [] }
const event: CompanyEvent = { event_id: 'filing-fixture', symbol: 'AAPL', event_type: 'sec_filing', title: 'Fixture earnings filing', description: 'Published fixture result', scheduled_at: null, released_at: '2026-10-13T20:00:00Z', importance: 'high', status: 'released', source: 'test-fixture', source_url: 'https://www.sec.gov/Archives/', source_id: 'fixture-source', timezone: 'UTC', actual: null, forecast: null, previous: null, unit: null, first_seen_at: '2026-10-14', last_seen_at: '2026-10-14', created_at: '2026-10-14', updated_at: '2026-10-14', content_hash: 'fixture', metadata: { eps_actual: '1.23', form: '8-K' } }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/stocks/AAPL']}><Routes><Route path="/stocks/:symbol" element={<StockPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: {} })
  vi.spyOn(api, 'getStockDetail').mockResolvedValue(stock)
  vi.spyOn(api, 'getInterpretation').mockResolvedValue(interpretation)
  vi.spyOn(api, 'getBars').mockResolvedValue({ symbol: 'AAPL', timeframe: '1Day', bars: [], status: 'empty', reason: 'No stored bars', source: 'test-fixture', mode: 'demo' })
  vi.spyOn(api, 'getEarnings').mockResolvedValue([event])
  vi.spyOn(api, 'getEvents').mockResolvedValue([])
  vi.spyOn(api, 'getNews').mockResolvedValue([])
  vi.spyOn(api, 'getInsiders').mockResolvedValue([])
  vi.spyOn(api, 'getFilings').mockResolvedValue([])
  vi.spyOn(api, 'getQuantSignals').mockResolvedValue(quant)
  vi.spyOn(api, 'getLeadership').mockResolvedValue({ symbol: 'AAPL', leadership: { ceo: { name: 'Evidence CEO', effective_date: null, event_id: 'ceo-filing', source: 'test-fixture', source_url: 'https://www.sec.gov/Archives/', released_at: '2026-10-13' }, cfo: { name: 'Evidence CFO', effective_date: '2026-10-01', event_id: 'cfo-filing', source: 'test-fixture', source_url: null, released_at: '2026-10-13' } } })
})
afterEach(() => vi.restoreAllMocks())

describe('StockPage actual Phase 9 and evidence contracts', () => {
  it('uses route symbol and actual metadata/zero daily close', async () => {
    mount()
    expect(screen.getByRole('heading', { level: 1, name: 'AAPL' })).toBeInTheDocument()
    expect(await screen.findByText('Apple fixture · NASDAQ')).toBeInTheDocument()
    expect(screen.getByText('$0.00')).toBeInTheDocument()
    expect(api.getStockDetail).toHaveBeenCalledWith('AAPL')
    expect(screen.getByText(/Latest completed daily close, not a live quote/)).toBeInTheDocument()
  })
  it('renders all accessible stock tabs and linked panel', () => {
    mount()
    for (const tab of ['Overview', 'Earnings', 'Events', 'News', 'Insiders', 'Leadership', 'Filings', 'Quant']) expect(screen.getByRole('tab', { name: tab })).toHaveAttribute('aria-controls', 'stock-panel')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'stock-tab-overview')
  })
  it('defaults to overview and renders actual interpretation narrative', async () => {
    mount()
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByRole('heading', { name: 'What You Need to Know' })).toBeInTheDocument()
    expect(screen.getByText(interpretation.what_happened)).toBeInTheDocument()
    expect(screen.getByText(interpretation.why_it_matters)).toBeInTheDocument()
  })
  it('switches to earnings and displays full MarketEvent evidence with provider metadata', async () => {
    mount(); fireEvent.click(screen.getByRole('tab', { name: 'Earnings' }))
    expect(screen.getByRole('tab', { name: 'Earnings' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByRole('heading', { name: event.title })).toBeInTheDocument()
    expect(screen.getByText(/test\/demo provenance, not live evidence/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Provider fields & provenance'))
    expect(screen.getByText('eps actual')).toBeInTheDocument()
    expect(screen.getByText('1.23')).toBeInTheDocument()
    expect(api.getEarnings).toHaveBeenCalledWith('AAPL')
  })
  it('keeps company impact separate from mixed stock bias', async () => {
    mount()
    const company = (await screen.findByRole('heading', { name: 'Company Impact' })).closest('article')!
    const stockImpact = screen.getByRole('heading', { name: 'Stock Impact' }).closest('article')!
    expect(within(company).getByText('positive')).toBeInTheDocument()
    expect(within(company).getByText('Company fixture reason')).toBeInTheDocument()
    expect(within(stockImpact).getByText('mixed')).toBeInTheDocument()
    expect(within(stockImpact).queryByText('Company fixture reason')).not.toBeInTheDocument()
  })
  it('renders all conditional scenarios without fabricating null probability bands', async () => {
    mount()
    await screen.findByRole('heading', { name: 'Scenario Analysis' })
    for (const name of ['BASE CASE', 'BULL CASE', 'BEAR CASE']) expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    expect(screen.getAllByText('Verify primary release')).toHaveLength(3)
    expect(screen.queryByText(/Backend probability band/)).not.toBeInTheDocument()
  })
  it('renders supplied what-would-change-view conditions', async () => {
    mount()
    expect(await screen.findByRole('heading', { name: 'What Would Change the View?' })).toBeInTheDocument()
    expect(screen.getByText('Primary release')).toBeInTheDocument()
    expect(screen.getByText('Verify a new official statement')).toBeInTheDocument()
  })
  it('preserves actual confidence assessment and reasons', async () => {
    mount()
    expect(await screen.findByText('Confidence & missing information')).toBeInTheDocument()
    expect(screen.getAllByText('Confidence: 75%')).toHaveLength(2)
    expect(screen.getByText('Primary source')).toBeInTheDocument()
  })
  it('makes missing evidence explicit rather than promising complete coverage', async () => {
    mount()
    expect(await screen.findByRole('heading', { name: 'Missing Information' })).toBeInTheDocument()
    expect(screen.getByText('No recent earnings result available')).toBeInTheDocument()
  })
  it('expands traceable evidence references and actual source URLs', async () => {
    mount()
    const disclosure = await screen.findByText('Supporting Evidence (1)')
    fireEvent.click(disclosure)
    expect(disclosure.closest('details')).toHaveAttribute('open')
    expect(screen.getByText('Primary filing evidence')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View source' })).toHaveAttribute('href', 'https://www.sec.gov/Archives/')
    expect(screen.getByText('Evidence ID: fixture-evidence')).toBeInTheDocument()
  })
  it('empty earnings retains an honest no-records state', async () => {
    vi.mocked(api.getEarnings).mockResolvedValue([])
    mount(); fireEvent.click(screen.getByRole('tab', { name: 'Earnings' }))
    expect(await screen.findByText('No earnings records available.')).toBeInTheDocument()
    expect(screen.queryByText(event.title)).not.toBeInTheDocument()
  })
  it('derives CEO/CFO from response evidence, never hardcodes historic leaders', async () => {
    mount(); fireEvent.click(screen.getByRole('tab', { name: 'Leadership' }))
    expect(await screen.findByText('Evidence CEO')).toBeInTheDocument()
    expect(screen.getByText('Evidence CFO')).toBeInTheDocument()
    expect(screen.getByText(/Event: ceo-filing/)).toBeInTheDocument()
    expect(screen.queryByText('Tim Cook')).not.toBeInTheDocument()
    expect(screen.queryByText('Luca Maestri')).not.toBeInTheDocument()
  })
  it('shows actual quant signals, zero score and backend rank', async () => {
    mount(); fireEvent.click(screen.getByRole('tab', { name: 'Quant' }))
    expect(await screen.findByRole('heading', { name: 'Quant Signals' })).toBeInTheDocument()
    expect(screen.getByText(/Score: 0.0 · Rank: 7/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'momentum 20d' })).toBeInTheDocument()
    expect(screen.getAllByText('0.00')).toHaveLength(2)
  })
  it('unknown metadata/price stays unavailable, while deterministic answer uses actual schema', async () => {
    vi.mocked(api.getStockDetail).mockResolvedValue({ ...stock, price: null, name: null, exchange: null })
    vi.spyOn(api, 'answerQuestion').mockResolvedValue({ question: 'Why?', answer: 'Evidence is incomplete', confidence: 0, generated_at: '2026-10-14', evidence_refs: [] })
    mount()
    expect(await screen.findByText('Company name unavailable · Exchange unavailable')).toBeInTheDocument()
    expect(screen.getByText('Price unavailable')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Research question' }), { target: { value: 'Why?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ask', exact: true }))
    expect(await screen.findByText('Evidence is incomplete')).toBeInTheDocument()
    expect(api.answerQuestion).toHaveBeenCalledWith('AAPL', 'Why?')
    expect(screen.getByText('Confidence: 0%')).toBeInTheDocument()
  })
})
