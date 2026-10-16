import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import type { Alert, AlertTrigger, CompanyEvent } from '../services/api'
import { EventTiming, ProviderCoverage, Term } from '../components/ui/ResearchData'
import { AlertsPage } from './AlertsPage'
import { StockPage } from './StockPage'
import { LandingPage } from './LandingPage'

function mount(node: React.ReactNode, route = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><Routes><Route path={route.startsWith('/stocks/') ? '/stocks/:symbol' : route} element={node} /></Routes></MemoryRouter></QueryClientProvider>)
}
afterEach(() => vi.restoreAllMocks())

describe('bounded frontend repair contracts', () => {
  it('preserves a touched term across synthetic hover exit, with keyboard close', async () => {
    vi.spyOn(api, 'getTermDefinition').mockResolvedValue({ term: 'EPS', short_definition: 'Earnings per share', long_definition: null, category: 'financial', reference_type: 'SEC', external_reference_url: 'https://www.sec.gov', related_terms: [] })
    mount(<Term term="EPS" />)
    const button = screen.getByRole('button', { name: 'EPS' })
    fireEvent.touchStart(button)
    fireEvent.mouseEnter(button)
    fireEvent.click(button)
    fireEvent.mouseLeave(button)
    expect(await screen.findByText('Earnings per share')).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-expanded', 'true')
    fireEvent.keyDown(button, { key: 'Escape' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })

  it('shows date-only session precision without a fabricated timestamp', () => {
    mount(<EventTiming event={{ scheduled_at: null, metadata: { event_date: '2026-10-29', session: 'AMC' } }} />)
    expect(screen.getByText('2026-10-29 · Exact time unknown · Session: AMC')).toBeInTheDocument()
    expect(screen.queryByText(/00:00/)).not.toBeInTheDocument()
  })

  it('distinguishes failed, partial, unrefreshed and empty providers and scopes refresh', async () => {
    vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: { sec: { status: 'provider_error', reason: 'Source request failed' }, macro: { status: 'partial' }, news: { status: 'not_refreshed' }, earnings: { status: 'empty' } } })
    const refresh = vi.spyOn(api, 'refreshMarketData').mockResolvedValue({ status: 'completed', symbols: ['AAPL'], state: {} })
    mount(<ProviderCoverage symbol="AAPL" />)
    expect(await screen.findByText(/Source request failed/)).toBeInTheDocument()
    expect(screen.getByText(/: partial/)).toBeInTheDocument()
    expect(screen.getByText(/: not_refreshed/)).toBeInTheDocument()
    expect(screen.getByText(/: empty/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh evidence for AAPL' }))
    await waitFor(() => expect(refresh).toHaveBeenCalledWith(['AAPL']))
    expect(await screen.findByRole('status')).toHaveTextContent('does not mean all sources succeeded')
  })

  it('groups future date-only macro evidence as upcoming rather than unknown/past', async () => {
    vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: {} })
    vi.spyOn(api, 'getMarketOverview').mockRejectedValue(new Error('offline fixture'))
    vi.spyOn(api, 'getQuantScannerTop').mockResolvedValue([])
    vi.spyOn(api, 'getRecentEvents').mockResolvedValue([])
    vi.spyOn(api, 'getWatchlists').mockResolvedValue([])
    const date = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
    vi.spyOn(api, 'getMacroEvents').mockResolvedValue([{ event_id: 'fed', title: 'FOMC date-only fixture', event_type: 'macro', scheduled_at: null, released_at: null, metadata: { event_date: date }, status: 'scheduled', importance: 'high', source: 'fixture', source_url: null, actual: null, forecast: null, previous: null }])
    mount(<LandingPage />)
    const heading = await screen.findByRole('heading', { name: 'Upcoming — next 30 days' })
    expect(within(heading.parentElement!).getByText(`${date} · Exact time unknown`)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Past schedule / release date unconfirmed' })).not.toBeInTheDocument()
  })

  it('renders management attribution and exact evidence only from retained metadata', async () => {
    vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: {} })
    vi.spyOn(api, 'getStockDetail').mockRejectedValue(new Error('offline fixture'))
    vi.spyOn(api, 'getInterpretation').mockRejectedValue(new Error('offline fixture'))
    vi.spyOn(api, 'getBars').mockRejectedValue(new Error('offline fixture'))
    vi.spyOn(api, 'getEvents').mockResolvedValue([{ event_id: 'event-fixture', metadata: { management_statements: [{ statement_id: 's', speaker: 'Fixture CEO', speaker_role: 'CEO', statement: 'Demand strengthened.', statement_type: 'demand', source_type: 'ir_release', source_document_id: 'document-fixture', source_url: 'https://www.apple.com/newsroom/', evidence_span: { start: 0, end: 40, text: 'Fixture CEO said, “Demand strengthened.”' }, extraction_method: 'deterministic', published_at: '2026-10-14T12:00:00Z', retrieved_at: '2026-10-14T13:00:00Z', event_date: null }] } } as unknown as CompanyEvent])
    mount(<StockPage />, '/stocks/AAPL')
    fireEvent.click(screen.getByRole('tab', { name: 'Management' }))
    expect(await screen.findByText('Fixture CEO said, “Demand strengthened.”')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Fixture CEO · CEO' })).toBeInTheDocument()
    expect(screen.getByText(/Statement date: Date unavailable/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View source' })).toHaveAttribute('href', 'https://www.apple.com/newsroom/')
  })

  it('evaluates one rule, refreshes genuine history contract, and acknowledges provenance', async () => {
    const alert = { id: 'a', name: 'Fixture manual rule', alert_type: 'price', condition: 'above', threshold: 1, symbols: ['AAPL'], channels: ['in_app'], severity: 'info', is_active: true, trigger_count: 0, cooldown_minutes: 60 } as Alert
    const observation = { source: 'Fixture daily provider', as_of: '2026-10-14T20:00:00Z', price: 200 }
    let triggers: AlertTrigger[] = []
    vi.spyOn(api, 'getAlerts').mockImplementation(async () => [{ ...alert, trigger_count: triggers.length }])
    vi.spyOn(api, 'getRecentAlertTriggers').mockImplementation(async () => triggers)
    const evaluate = vi.spyOn(api, 'evaluateAlert').mockImplementation(async () => {
      triggers = [{ id: 't', alert_id: 'a', symbol: 'AAPL', severity: 'info', message: 'Fixture match recorded', value: 200, threshold: 1, triggered_at: '2026-10-15T12:00:00Z', acknowledged: false, metadata: { observation } } as AlertTrigger]
      return { status: 'evaluated', would_trigger: true, symbols_checked: ['AAPL'], current_values: { AAPL: observation }, triggers, delivery: 'in_app_history_only', message: 'Manual local evaluation only.' }
    })
    const acknowledge = vi.spyOn(api, 'acknowledgeAlertTrigger').mockImplementation(async () => { triggers = triggers.map(t => ({ ...t, acknowledged: true })) })
    mount(<AlertsPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Evaluate', exact: true }))
    expect(await screen.findByText('Status: evaluated · Recorded triggers: 1')).toBeInTheDocument()
    expect(evaluate).toHaveBeenCalledWith('a')
    expect(screen.getByText(/Observation source: Fixture daily provider/)).toHaveTextContent('2026-10-14T20:00:00Z')
    fireEvent.click(screen.getByRole('button', { name: 'View trigger history' }))
    expect(await screen.findByText('Fixture match recorded')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge', exact: true }))
    expect(await screen.findByText('Acknowledged')).toBeInTheDocument()
    expect(acknowledge).toHaveBeenCalledWith('t')
    expect(screen.getByText(/it is not live monitoring/)).toBeInTheDocument()
  })

  it('does not call unavailable manual evaluation a no-match or create history', async () => {
    vi.spyOn(api, 'getAlerts').mockResolvedValue([{ id: 'a', name: 'Missing provider', symbols: ['AAPL'], channels: [], severity: 'info', is_active: true, threshold: 1 } as unknown as Alert])
    vi.spyOn(api, 'getRecentAlertTriggers').mockResolvedValue([])
    vi.spyOn(api, 'evaluateAlert').mockResolvedValue({ status: 'unavailable', would_trigger: null, symbols_checked: [], current_values: {}, triggers: [], delivery: 'in_app_history_only' })
    mount(<AlertsPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Evaluate', exact: true }))
    expect(await screen.findByText('Observations unavailable; no match can be determined.')).toBeInTheDocument()
    expect(screen.getByText('Status: unavailable · Recorded triggers: 0')).toBeInTheDocument()
  })
})
