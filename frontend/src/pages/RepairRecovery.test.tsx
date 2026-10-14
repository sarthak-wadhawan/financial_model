import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { api } from '../services/api'
import { ThemeProvider } from '../context/ThemeContext'
import App from '../App'
import { MacroCalendarPage } from './MacroCalendarPage'

function renderWithProviders(page: React.ReactNode, route: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><ThemeProvider>{page}</ThemeProvider></MemoryRouter></QueryClientProvider>)
}

const watchlist = { id: 'repair-list-1', name: 'Recovery research', description: 'Test fixture only', sort_order: 'manual' as const, is_default: false, created_at: '2026-10-14', updated_at: '2026-10-14', item_count: 1, symbols: ['AAPL'] }
function mockWatchlists() {
  vi.spyOn(api, 'getWatchlists').mockResolvedValue([watchlist])
  return vi.spyOn(api, 'getWatchlist').mockResolvedValue({ ...watchlist, items: [{ symbol: 'AAPL', notes: 'Retained research note', added_at: '2026-10-14', sort_index: 0 }] })
}

describe('targeted E/G/I recovery', () => {
  it('navigates real App → existing WatchlistPage → detail route without mocking the page/router', async () => {
    const detail = mockWatchlists()
    renderWithProviders(<App />, '/watchlists')
    fireEvent.click(await screen.findByRole('link', { name: 'Open Recovery research' }))
    expect(await screen.findByRole('button', { name: 'Add Symbol' })).toBeInTheDocument()
    expect(screen.getByText('Retained research note')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AAPL' })).toHaveAttribute('href', '/stocks/AAPL')
    expect(detail).toHaveBeenCalledWith('repair-list-1')
    fireEvent.click(screen.getByRole('link', { name: 'All Watchlists' }))
    expect(await screen.findByRole('link', { name: 'Open Recovery research' })).toBeInTheDocument()
  })
  it('resolves direct watchlist detail URLs in the real App routing table', async () => {
    const detail = mockWatchlists()
    renderWithProviders(<App />, '/watchlists/repair-list-1')
    expect(await screen.findByRole('heading', { name: 'Recovery research' })).toBeInTheDocument()
    expect(detail).toHaveBeenCalledWith('repair-list-1')
    expect(screen.queryByText('Page Not Found')).not.toBeInTheDocument()
  })
  it.each(['javascript:alert(1)', 'https://user@www.bls.gov/release'])('retains macro source/evidence but rejects its unsafe URL: %s', source_url => {
    const event = Object.freeze({ event_id: 'macro-recovery', title: 'Retained macro event', event_type: 'CPI', scheduled_at: '2026-10-20', released_at: null, actual: '0', forecast: null, previous: null, importance: 'high', status: 'scheduled', source: 'BLS', source_url })
    vi.spyOn(api, 'getMacroEvents').mockResolvedValue([event])
    renderWithProviders(<MacroCalendarPage />, '/macro')
    return screen.findByText('Retained macro event').then(() => {
      expect(screen.getByText('BLS — link unavailable')).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /BLS/ })).not.toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument()
      expect(screen.getByLabelText('Importance')).toBeInTheDocument()
      expect(screen.getByLabelText('Event Type')).toBeInTheDocument()
      expect(event.source_url).toBe(source_url)
    })
  })
  it('treats a macro request failure as failure, not no events', async () => {
    vi.spyOn(api, 'getMacroEvents').mockRejectedValue(new Error('offline'))
    renderWithProviders(<MacroCalendarPage />, '/macro')
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Could not load macro events'))
    expect(screen.queryByRole('heading', { name: 'No events found' })).not.toBeInTheDocument()
  })
})
