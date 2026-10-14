import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WatchlistPage } from './WatchlistPage'
import { AlertsPage } from './AlertsPage'
import { CalendarPage } from './CalendarPage'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: {
  getWatchlists: vi.fn(), getWatchlist: vi.fn(), addWatchlistItem: vi.fn(), updateWatchlistItem: vi.fn(), reorderWatchlistItems: vi.fn(),
  getAlerts: vi.fn(), getRecentAlertTriggers: vi.fn(), testAlert: vi.fn(), acknowledgeAlertTrigger: vi.fn(), exportCalendar: vi.fn(),
} }))

function mount(page: React.ReactNode, path: string, route = path) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path={route} element={page} /></Routes></MemoryRouter></QueryClientProvider>)
}

const watchlist = { id: 'wl', name: 'Research', description: null, sort_order: 'manual' as const, is_default: false, created_at: '2026-10-14', updated_at: '2026-10-14', item_count: 2, symbols: ['AAPL', 'MSFT'], items: [
  { symbol: 'AAPL', notes: 'Original', added_at: '2026-10-14', sort_index: 0 }, { symbol: 'MSFT', notes: null, added_at: '2026-10-14', sort_index: 1 },
] }

beforeEach(() => { vi.clearAllMocks() })

describe('Phase 11 repair', () => {
  it('renders the Add Symbol dialog on detail, submits dotted ticker and notes', async () => {
    vi.mocked(api.getWatchlists).mockResolvedValue([watchlist])
    vi.mocked(api.getWatchlist).mockResolvedValue(watchlist)
    vi.mocked(api.addWatchlistItem).mockResolvedValue({ symbol: 'BRK.B', notes: 'Research note', added_at: '2026-10-14', sort_index: 2 })
    mount(<WatchlistPage />, '/watchlists/wl', '/watchlists/:watchlistId')
    fireEvent.click(await screen.findByRole('button', { name: 'Add Symbol' }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Symbol'), { target: { value: 'brk.b' } })
    fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'Research note' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.addWatchlistItem).toHaveBeenCalledWith('wl', { symbol: 'BRK.B', notes: 'Research note' }))
  })

  it('reorders exact membership and updates editable notes', async () => {
    vi.mocked(api.getWatchlists).mockResolvedValue([watchlist])
    vi.mocked(api.getWatchlist).mockResolvedValue(watchlist)
    vi.mocked(api.reorderWatchlistItems).mockResolvedValue({ success: true })
    mount(<WatchlistPage />, '/watchlists/wl', '/watchlists/:watchlistId')
    fireEvent.click(await screen.findByRole('button', { name: 'Move MSFT up' }))
    await waitFor(() => expect(api.reorderWatchlistItems).toHaveBeenCalledWith('wl', ['MSFT', 'AAPL']))
    fireEvent.click(screen.getByRole('button', { name: 'Edit Notes for AAPL' }))
    fireEvent.change(screen.getByLabelText('Notes'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateWatchlistItem).toHaveBeenCalledWith('wl', 'AAPL', { notes: '' }))
  })

  it('does not disguise failed alerts query as an empty list', async () => {
    vi.mocked(api.getAlerts).mockRejectedValue(new Error('offline'))
    vi.mocked(api.getRecentAlertTriggers).mockResolvedValue([])
    mount(<AlertsPage />, '/alerts')
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load or save')
    expect(screen.queryByText('No alerts found')).not.toBeInTheDocument()
  })

  it('labels calendar date/session semantics and validates reversed bounds', async () => {
    mount(<CalendarPage />, '/calendar')
    expect(screen.getByText(/not a midnight release/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Export Calendar' }))
    fireEvent.change(screen.getByLabelText('From Date'), { target: { value: '2026-10-15' } })
    fireEvent.change(screen.getByLabelText('To Date'), { target: { value: '2026-10-14' } })
    fireEvent.click(screen.getByRole('button', { name: 'Export & Download .ics' }))
    expect(screen.getByRole('alert')).toHaveTextContent('From date must not be after')
    expect(api.exportCalendar).not.toHaveBeenCalled()
  })
})
