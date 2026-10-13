import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { Badge, Modal, ConfirmDialog } from '../components/ui'
import type { WatchlistCreate, WatchlistUpdate } from '../services/api'

export function WatchlistPage() {
  const { watchlistId } = useParams<{ watchlistId?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAddSymbolModal, setShowAddSymbolModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)
  const [newWatchlistName, setNewWatchlistName] = useState('')
  const [newWatchlistDescription, setNewWatchlistDescription] = useState('')
  const [newWatchlistSortOrder, setNewWatchlistSortOrder] = useState<'manual' | 'symbol' | 'quant_score' | 'price_change' | 'market_cap'>('manual')
  const [newSymbol, setNewSymbol] = useState('')
  const [newSymbolNotes, setNewSymbolNotes] = useState('')
  const [symbolError, setSymbolError] = useState('')

  const { data: watchlists, isLoading: watchlistsLoading, error: watchlistsError } = useQuery({
    queryKey: ['watchlists'],
    queryFn: () => api.getWatchlists(),
    staleTime: 1000 * 60 * 5,
  })

  const { data: watchlist, isLoading: watchlistLoading } = useQuery({
    queryKey: ['watchlist', watchlistId],
    queryFn: () => api.getWatchlist(watchlistId!),
    enabled: !!watchlistId,
    staleTime: 1000 * 60 * 5,
  })

  const createMutation = useMutation({
    mutationFn: (watchlist: WatchlistCreate) => api.createWatchlist(watchlist),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
      setShowCreateModal(false)
      setNewWatchlistName('')
      setNewWatchlistDescription('')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: string; update: WatchlistUpdate }) => api.updateWatchlist(id, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
      if (watchlistId) queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteWatchlist(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
      setShowDeleteConfirm(null)
      if (watchlistId) navigate('/watchlists')
    },
  })

  const removeItemMutation = useMutation({
    mutationFn: ({ watchlistId, symbol }: { watchlistId: string; symbol: string }) => api.removeWatchlistItem(watchlistId, symbol),
    onSuccess: () => {
      if (watchlistId) queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] })
    },
  })

  const addSymbolMutation = useMutation({
    mutationFn: ({ watchlistId, item }: { watchlistId: string; item: { symbol: string; notes?: string } }) => api.addWatchlistItem(watchlistId, item),
    onSuccess: () => {
      if (watchlistId) queryClient.invalidateQueries({ queryKey: ['watchlist', watchlistId] })
      setShowAddSymbolModal(false)
      setNewSymbol('')
      setNewSymbolNotes('')
      setSymbolError('')
    },
    onError: (error: any) => {
      setSymbolError(error?.response?.data?.detail || 'Failed to add symbol. Please try again.')
    },
  })

  const handleAddSymbol = (e: React.FormEvent) => {
    e.preventDefault()
    setSymbolError('')
    const symbol = newSymbol.trim().toUpperCase()
    if (!symbol) {
      setSymbolError('Symbol is required')
      return
    }
    if (!/^[A-Z]{1,5}$/.test(symbol)) {
      setSymbolError('Invalid symbol format (1-5 letters)')
      return
    }
    if (watchlist?.items.some(item => item.symbol === symbol)) {
      setSymbolError('Symbol already in watchlist')
      return
    }
    addSymbolMutation.mutate({
      watchlistId: watchlistId!,
      item: { symbol, notes: newSymbolNotes.trim() || undefined },
    })
  }

  const handleCreateWatchlist = (e: React.FormEvent) => {
    e.preventDefault()
    if (newWatchlistName.trim()) {
      createMutation.mutate({
        name: newWatchlistName.trim(),
        description: newWatchlistDescription.trim() || undefined,
        sort_order: newWatchlistSortOrder,
      })
    }
  }

  if (watchlistsLoading) {
    return (
      <div className="page watchlist-page">
        <div className="page-header">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (watchlistsError) {
    return (
      <div className="page watchlist-page">
        <div className="page-header">
          <h1>Watchlists</h1>
          <p className="page-subtitle">Manage your watchlists</p>
        </div>
        <div className="error-state">
          <p>Failed to load watchlists. Please try again.</p>
        </div>
      </div>
    )
  }

  // Detail view
  if (watchlistId) {
    if (watchlistLoading) {
      return (
        <div className="page watchlist-page">
          <div className="page-header">
            <LoadingSpinner size="lg" />
          </div>
        </div>
      )
    }

    if (!watchlist) {
      return (
        <div className="page watchlist-page">
          <div className="page-header">
            <h1>Watchlist Not Found</h1>
          </div>
          <p>This watchlist doesn't exist or has been deleted.</p>
          <Link to="/watchlists" className="btn btn-primary">Back to Watchlists</Link>
        </div>
      )
    }

    return (
      <div className="page watchlist-page">
        <div className="page-header">
          <div className="page-header-content">
            <h1>{watchlist.name}</h1>
            <p className="page-subtitle">{watchlist.description || 'No description'}</p>
          </div>
          <div className="page-header-actions">
            <button className="btn btn-primary" onClick={() => setShowAddSymbolModal(true)}>
              Add Symbol
            </button>
            <button className="btn btn-secondary" onClick={() => updateMutation.mutate({ id: watchlist.id, update: { is_default: true } })}>
              {watchlist.is_default ? 'Default' : 'Set as Default'}
            </button>
          </div>
        </div>

        <div className="watchlist-content">
          <div className="watchlist-toolbar">
            <div className="watchlist-info">
              <span className="sort-badge">{watchlist.sort_order}</span>
              <span className="item-count">{watchlist.item_count} symbols</span>
              <span className="updated">Updated {format(new Date(watchlist.updated_at), 'MMM d, yyyy HH:mm')}</span>
            </div>
          </div>

          {watchlist.items.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <h3>No symbols in this watchlist</h3>
              <p>Add symbols to start tracking</p>
              <button className="btn btn-primary" onClick={() => setShowAddSymbolModal(true)}>
                Add Symbol
              </button>
            </div>
          ) : (
            <div className="watchlist-table-container">
              <table className="watchlist-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Symbol</th>
                    <th>Notes</th>
                    <th>Added</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {watchlist.items.map((item, index) => (
                    <tr key={item.symbol}>
                      <td className="rank">{index + 1}</td>
                      <td>
                        <Link to={`/stocks/${item.symbol}`} className="symbol-link">
                          {item.symbol}
                        </Link>
                      </td>
                      <td className="notes">{item.notes || <span className="muted">—</span>}</td>
                      <td className="date-cell">{format(new Date(item.added_at), 'MMM d, yyyy')}</td>
                      <td>
                        <button
                          className="btn btn-sm btn-ghost"
                          onClick={() => removeItemMutation.mutate({ watchlistId: watchlist.id, symbol: item.symbol })}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    )
  }

  // List view
  return (
    <div className="page watchlist-page">
      <div className="page-header">
        <div className="page-header-content">
          <h1>Watchlists</h1>
          <p className="page-subtitle">Manage your watchlists and track symbols</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          Create Watchlist
        </button>
      </div>

      {!watchlists || watchlists.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <h3>No watchlists yet</h3>
          <p>Create your first watchlist to start tracking symbols</p>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Create Watchlist
          </button>
        </div>
      ) : (
        <div className="watchlists-grid">
          {watchlists!.map((wl) => (
            <div key={wl.id} className="watchlist-card">
              <div className="watchlist-card-header">
                <h3>{wl.name}</h3>
                {wl.is_default && <Badge variant="success">Default</Badge>}
              </div>
              <p className="watchlist-description">{wl.description || <span className="muted">No description</span>}</p>
              <div className="watchlist-meta">
                <span className="meta-item">{wl.item_count} symbols</span>
                <span className="meta-item">Sort: {wl.sort_order}</span>
                <span className="meta-item">Updated {format(new Date(wl.updated_at), 'MMM d, yyyy')}</span>
              </div>
              <div className="watchlist-actions">
                <Link to={`/watchlists/${wl.id}`} className="btn btn-primary btn-sm">
                  Open
                </Link>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => updateMutation.mutate({ id: wl.id, update: { is_default: !wl.is_default } })}
                >
                  {wl.is_default ? 'Default' : 'Set Default'}
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowDeleteConfirm(wl.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Watchlist"
      >
        <form onSubmit={handleCreateWatchlist}>
          <div className="form-group">
            <label htmlFor="watchlist-name">Name</label>
            <input
              id="watchlist-name"
              type="text"
              value={newWatchlistName}
              onChange={(e) => setNewWatchlistName(e.target.value)}
              placeholder="My Watchlist"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="watchlist-description">Description (optional)</label>
            <textarea
              id="watchlist-description"
              value={newWatchlistDescription}
              onChange={(e) => setNewWatchlistDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
          </div>
          <div className="form-group">
            <label htmlFor="watchlist-sort">Default Sort Order</label>
            <select
              id="watchlist-sort"
              value={newWatchlistSortOrder}
              onChange={(e) => setNewWatchlistSortOrder(e.target.value as any)}
            >
              <option value="manual">Manual</option>
              <option value="symbol">Symbol</option>
              <option value="quant_score">Quant Score</option>
              <option value="price_change">Price Change</option>
              <option value="market_cap">Market Cap</option>
            </select>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Watchlist'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showAddSymbolModal}
        onClose={() => { setShowAddSymbolModal(false); setSymbolError(''); }}
        title="Add Symbol to Watchlist"
      >
        <form onSubmit={handleAddSymbol}>
          <div className="form-group">
            <label htmlFor="add-symbol">Symbol</label>
            <input
              id="add-symbol"
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="AAPL"
              required
              autoFocus
              maxLength={5}
            />
          </div>
          <div className="form-group">
            <label htmlFor="add-symbol-notes">Notes (optional)</label>
            <textarea
              id="add-symbol-notes"
              value={newSymbolNotes}
              onChange={(e) => setNewSymbolNotes(e.target.value)}
              placeholder="Optional notes about this symbol"
              rows={3}
            />
          </div>
          {symbolError && <div className="error-message">{symbolError}</div>}
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => { setShowAddSymbolModal(false); setSymbolError(''); }}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={addSymbolMutation.isPending}>
              {addSymbolMutation.isPending ? 'Adding...' : 'Add Symbol'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(null)}
        onConfirm={() => deleteMutation.mutate(showDeleteConfirm!)}
        title="Delete Watchlist"
        message="Are you sure you want to delete this watchlist? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

export default WatchlistPage