import { render, screen, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, type CompanyEvent } from '../services/api'
import { MacroCalendarPage } from './MacroCalendarPage'

const upcoming: CompanyEvent = { event_id: 'fomc-fixture', title: 'Fixture FOMC decision', symbol: null, event_type: 'fomc', scheduled_at: '2026-10-28T18:00:00Z', released_at: null, timezone: 'UTC', importance: 'critical', status: 'scheduled', source: 'test-fixture', source_url: 'https://www.federalreserve.gov/', source_id: 'fixture-fomc', description: null, actual: null, forecast: null, previous: null, unit: null, first_seen_at: '2026-10-14', last_seen_at: '2026-10-14', created_at: '2026-10-14', updated_at: '2026-10-14', content_hash: 'fixture', metadata: {} }
const released: CompanyEvent = { ...upcoming, event_id: 'cpi-fixture', title: 'Fixture CPI release', event_type: 'cpi', importance: 'high', status: 'released', scheduled_at: '2026-10-13T12:30:00Z', released_at: '2026-10-13T12:30:00Z', actual: '0', forecast: '0.1', previous: '0.2', source_id: 'fixture-cpi' }
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><MacroCalendarPage /></QueryClientProvider>)
}
async function loaded() { await screen.findByRole('heading', { name: 'Macro Calendar' }) }
beforeEach(() => {
  vi.spyOn(api, 'getProviderCoverage').mockResolvedValue({ providers: {} })
  vi.spyOn(api, 'getMacroEvents').mockResolvedValue([upcoming, released])
})
afterEach(() => vi.restoreAllMocks())

describe('MacroCalendarPage full MarketEvent records', () => {
  it('renders actual page and queries supported macro endpoint', async () => {
    mount(); await loaded()
    expect(screen.getByText(/Track market-moving economic events/)).toBeInTheDocument()
    expect(api.getMacroEvents).toHaveBeenCalledWith({ limit: 100 })
  })
  it('renders labelled importance filter and all supported options', async () => {
    mount(); await loaded()
    expect(screen.getByLabelText('Importance')).toHaveValue('all')
    for (const name of ['All Importance', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']) expect(screen.getByRole('option', { name, exact: true })).toBeInTheDocument()
  })
  it('renders labelled macro type filter options', async () => {
    mount(); await loaded()
    expect(screen.getByLabelText('Event Type')).toHaveValue('all')
    for (const name of ['All Types', 'FOMC', 'CPI', 'NFP']) expect(screen.getByRole('option', { name, exact: true })).toBeInTheDocument()
  })
  it('exposes accessible Upcoming/Recent/All Events navigation', async () => {
    mount(); await loaded()
    for (const name of ['Upcoming', 'Recent', 'All Events']) expect(screen.getByRole('tab', { name })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Upcoming' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'tab-upcoming')
  })
  it('renders precise event table headers and original scheduled date', async () => {
    mount(); await loaded()
    for (const name of ['Date', 'Event', 'Type', 'Actual', 'Forecast', 'Previous', 'Importance', 'Status', 'Source']) expect(screen.getByRole('columnheader', { name })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /Fixture FOMC decision/ })).toHaveTextContent('2026-10-28')
    expect(screen.queryByText(released.title)).not.toBeInTheDocument()
  })
  it('retains importance guidance without substituting it for real data', async () => {
    mount(); await loaded()
    expect(screen.getByRole('heading', { name: 'Importance Levels' })).toBeInTheDocument()
    for (const value of ['Market-moving events (FOMC, NFP, CPI)', 'Significant market impact expected', 'Moderate market impact', 'Minor market impact']) expect(screen.getByText(value)).toBeInTheDocument()
  })
  it('retains status legend without confusing it with row status', async () => {
    mount(); await loaded()
    expect(screen.getByRole('heading', { name: 'Status' })).toBeInTheDocument()
    const legend = screen.getByRole('heading', { name: 'Status' }).parentElement!
    for (const value of ['RELEASED', 'SCHEDULED', 'UPDATED']) expect(within(legend).getByText(value, { exact: true })).toBeInTheDocument()
  })
  it('importance filter operates on lowercase backend values and changes rows', async () => {
    mount(); await loaded()
    fireEvent.click(screen.getByRole('tab', { name: 'All Events' }))
    fireEvent.change(screen.getByLabelText('Importance'), { target: { value: 'HIGH' } })
    expect(screen.getByText(released.title)).toBeInTheDocument()
    expect(screen.queryByText(upcoming.title)).not.toBeInTheDocument()
  })
  it('type filter operates on lowercase backend values and changes rows', async () => {
    mount(); await loaded()
    fireEvent.click(screen.getByRole('tab', { name: 'All Events' }))
    fireEvent.change(screen.getByLabelText('Event Type'), { target: { value: 'FOMC' } })
    expect(screen.getByText(upcoming.title)).toBeInTheDocument()
    expect(screen.queryByText(released.title)).not.toBeInTheDocument()
  })
  it('clears both filters and restores actual records', async () => {
    mount(); await loaded()
    fireEvent.click(screen.getByRole('tab', { name: 'All Events' }))
    fireEvent.change(screen.getByLabelText('Importance'), { target: { value: 'CRITICAL' } })
    fireEvent.change(screen.getByLabelText('Event Type'), { target: { value: 'CPI' } })
    expect(screen.getByText('No events found')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear Filters' }))
    expect(screen.getByLabelText('Importance')).toHaveValue('all')
    expect(screen.getByLabelText('Event Type')).toHaveValue('all')
    expect(screen.getByText(upcoming.title)).toBeInTheDocument()
    expect(screen.getByText(released.title)).toBeInTheDocument()
  })
  it('switching tabs changes records, preserves zero actual and publication precision', async () => {
    mount(); await loaded()
    fireEvent.click(screen.getByRole('tab', { name: 'Recent' }))
    expect(screen.getByRole('tab', { name: 'Recent' })).toHaveAttribute('aria-selected', 'true')
    const row = screen.getByRole('row', { name: /Fixture CPI release/ })
    expect(within(row).getByText('0', { exact: true })).toBeInTheDocument()
    expect(row).toHaveTextContent('Released (as supplied): 2026-10-13T12:30:00Z')
    expect(screen.queryByText(upcoming.title)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'All Events' }))
    expect(screen.getByText(upcoming.title)).toBeInTheDocument()
    expect(screen.getByText(released.title)).toBeInTheDocument()
  })
  it('labels test provenance and links the actual primary source', async () => {
    mount(); await loaded()
    const row = screen.getByRole('row', { name: /Fixture FOMC decision/ })
    expect(within(row).getByRole('link', { name: 'test-fixture' })).toHaveAttribute('href', upcoming.source_url)
    expect(row).toHaveTextContent('test/demo provenance, not live')
  })
  it('handles missing dates and forecasts without invented release times', async () => {
    vi.mocked(api.getMacroEvents).mockResolvedValue([{ ...upcoming, scheduled_at: null }])
    mount(); await loaded()
    const row = screen.getByRole('row', { name: /Fixture FOMC decision/ })
    expect(row).toHaveTextContent('Date unavailable')
    expect(within(row).getAllByText('Unknown')).toHaveLength(3)
    expect(within(row).queryByText(/Released \(as supplied\)/)).not.toBeInTheDocument()
  })
  it('exposes provider failure rather than passing it off as an empty calendar', async () => {
    vi.mocked(api.getMacroEvents).mockRejectedValueOnce(new Error('offline')).mockResolvedValue([upcoming])
    mount(); await loaded()
    expect(screen.getByRole('alert')).toHaveTextContent('Could not load macro events')
    expect(screen.queryByText('No events found')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry macro events' }))
    expect(await screen.findByText(upcoming.title)).toBeInTheDocument()
  })
})
