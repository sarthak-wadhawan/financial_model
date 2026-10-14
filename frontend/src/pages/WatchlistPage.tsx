import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { Badge, Modal, ConfirmDialog } from '../components/ui'

export function WatchlistPage() {
  const { watchlistId } = useParams<{ watchlistId?: string }>()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [dialog, setDialog] = useState<'create' | 'edit' | 'symbol' | 'notes' | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [symbol, setSymbol] = useState('')
  const [notes, setNotes] = useState('')
  const lists = useQuery({ queryKey: ['watchlists'], queryFn: () => api.getWatchlists() })
  const detail = useQuery({ queryKey: ['watchlist', watchlistId], queryFn: () => api.getWatchlist(watchlistId!), enabled: !!watchlistId })
  const wl = detail.data
  const mutation = useMutation({
    mutationFn: (operation: () => Promise<unknown>) => operation(),
    onSuccess: async () => {
      await Promise.all([client.invalidateQueries({ queryKey: ['watchlists'] }), client.invalidateQueries({ queryKey: ['watchlist'] })])
      setDialog(null)
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteWatchlist(id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['watchlists'] })
      setDeleteId(null)
      if (watchlistId) navigate('/watchlists')
    },
  })
  const open = (value: typeof dialog) => { mutation.reset(); setDialog(value) }
  const move = (index: number, direction: number) => {
    if (!wl) return
    const symbols = wl.items.map(item => item.symbol)
    ;[symbols[index], symbols[index + direction]] = [symbols[index + direction], symbols[index]]
    mutation.mutate(() => api.reorderWatchlistItems(wl.id, symbols))
  }
  const save = (event: React.FormEvent) => {
    event.preventDefault()
    if (dialog === 'create') mutation.mutate(() => api.createWatchlist({ name: name.trim(), description: description.trim(), sort_order: 'manual' }))
    if (dialog === 'edit' && wl) mutation.mutate(() => api.updateWatchlist(wl.id, { name: name.trim(), description }))
    if (dialog === 'symbol' && wl) mutation.mutate(() => api.addWatchlistItem(wl.id, { symbol: symbol.trim().toUpperCase(), notes }))
    if (dialog === 'notes' && wl) mutation.mutate(() => api.updateWatchlistItem(wl.id, symbol, { notes }))
  }
  const loading = lists.isLoading || (!!watchlistId && detail.isLoading)
  const failure = lists.error || (watchlistId && detail.error)
  return <div className="page watchlist-page">
    <div className="page-header">
      <div className="page-header-content"><h1>{wl?.name || 'Watchlists'}</h1><p className="page-subtitle">{wl?.description || 'Keep your research symbols and notes together.'}</p></div>
      <div className="page-header-actions">
        {watchlistId ? <>
          <Link className="btn btn-secondary" to="/watchlists">All Watchlists</Link>
          {wl && <>
            <button className="btn btn-primary" onClick={() => { setSymbol(''); setNotes(''); open('symbol') }}>Add Symbol</button>
            <button className="btn btn-secondary" onClick={() => { setName(wl.name); setDescription(wl.description || ''); open('edit') }}>Edit Watchlist</button>
            <button className="btn btn-secondary" disabled={mutation.isPending || wl.is_default} onClick={() => mutation.mutate(() => api.updateWatchlist(wl.id, { is_default: true }))}>{wl.is_default ? 'Default' : 'Set Default'}</button>
            <button className="btn btn-ghost" onClick={() => setDeleteId(wl.id)}>Delete</button>
          </>}
        </> : <button className="btn btn-primary" onClick={() => { setName(''); setDescription(''); open('create') }}>Create Watchlist</button>}
      </div>
    </div>
    {loading ? <LoadingSpinner size="lg" /> : failure ? <div className="error-state" role="alert"><p>Unable to load watchlists. This is not an empty list.</p><button className="btn btn-secondary" onClick={() => { lists.refetch(); detail.refetch() }}>Retry</button></div> : watchlistId ? wl ? <>
      <div className="watchlist-toolbar"><span>{wl.item_count} symbols · Manual ordering</span></div>
      {wl.items.length ? <div className="watchlist-table-container"><table className="watchlist-table"><thead><tr><th scope="col">Symbol</th><th scope="col">Notes</th><th scope="col">Actions</th></tr></thead><tbody>
        {wl.items.map((item, index) => <tr key={item.symbol}>
          <td><Link className="symbol-link" to={`/stocks/${encodeURIComponent(item.symbol)}`}>{item.symbol}</Link></td>
          <td>{item.notes || <span className="muted">No notes</span>}</td>
          <td><div className="watchlist-actions">
            <button className="btn btn-sm btn-secondary" onClick={() => { setSymbol(item.symbol); setNotes(item.notes || ''); open('notes') }}>Edit Notes<span className="sr-only"> for {item.symbol}</span></button>
            <button className="btn btn-sm btn-secondary" aria-label={`Move ${item.symbol} up`} disabled={index === 0 || mutation.isPending} onClick={() => move(index, -1)}>↑</button>
            <button className="btn btn-sm btn-secondary" aria-label={`Move ${item.symbol} down`} disabled={index === wl.items.length - 1 || mutation.isPending} onClick={() => move(index, 1)}>↓</button>
            <button className="btn btn-sm btn-ghost" aria-label={`Remove ${item.symbol}`} disabled={mutation.isPending} onClick={() => mutation.mutate(() => api.removeWatchlistItem(wl.id, item.symbol))}>Remove</button>
          </div></td>
        </tr>)}
      </tbody></table></div> : <div className="empty-state"><h2>No symbols yet</h2><p>Add a symbol to begin your research list.</p></div>}
    </> : <div className="empty-state"><h2>Watchlist not found</h2><Link to="/watchlists">Back to Watchlists</Link></div> : lists.data?.length ? <div className="watchlists-grid">
      {lists.data.map(item => <article className="watchlist-card" key={item.id}><div className="watchlist-card-header"><h2>{item.name}</h2>{item.is_default && <Badge variant="success">Default</Badge>}</div><p>{item.description || 'No description'}</p><p className="muted">{item.item_count} symbols</p><div className="watchlist-actions"><Link className="btn btn-primary" to={`/watchlists/${item.id}`}>Open {item.name}</Link><button className="btn btn-secondary" disabled={item.is_default || mutation.isPending} onClick={() => mutation.mutate(() => api.updateWatchlist(item.id, { is_default: true }))}>{item.is_default ? 'Default' : 'Set Default'}</button><button className="btn btn-ghost" onClick={() => setDeleteId(item.id)}>Delete</button></div></article>)}
    </div> : <div className="empty-state"><h2>No watchlists yet</h2><p>Create a watchlist to save symbols and notes.</p></div>}
    {(mutation.isError || remove.isError) && <p className="error-message" role="alert">Could not save changes. Check for a duplicate symbol or invalid input, then try again.</p>}
    <Modal isOpen={dialog !== null} onClose={() => setDialog(null)} title={dialog === 'create' ? 'Create Watchlist' : dialog === 'edit' ? 'Edit Watchlist' : dialog === 'notes' ? `Edit Notes for ${symbol}` : 'Add Symbol'}>
      <form onSubmit={save}>
        {(dialog === 'create' || dialog === 'edit') ? <>
          <div className="form-group"><label htmlFor="watchlist-name">Name</label><input id="watchlist-name" required maxLength={100} value={name} onChange={e => setName(e.target.value)} /></div>
          <div className="form-group"><label htmlFor="watchlist-description">Description</label><textarea id="watchlist-description" maxLength={500} value={description} onChange={e => setDescription(e.target.value)} /></div>
        </> : <>
          {dialog === 'symbol' && <div className="form-group"><label htmlFor="add-symbol">Symbol</label><input id="add-symbol" required maxLength={10} pattern="[A-Za-z][A-Za-z0-9.\-]{0,9}" value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="AAPL or BRK.B" /></div>}
          <div className="form-group"><label htmlFor="symbol-notes">Notes</label><textarea id="symbol-notes" maxLength={500} value={notes} onChange={e => setNotes(e.target.value)} /></div>
        </>}
        {mutation.isError && <p role="alert" className="error-message">Could not save. Duplicate symbols are not allowed.</p>}
        <div className="modal-footer"><button className="btn btn-secondary" type="button" onClick={() => setDialog(null)}>Cancel</button><button className="btn btn-primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save'}</button></div>
      </form>
    </Modal>
    <ConfirmDialog isOpen={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => remove.mutate(deleteId!)} title="Delete Watchlist" message="Delete this watchlist and its saved symbols? This cannot be undone." confirmText="Delete" variant="danger" loading={remove.isPending} />
  </div>
}

export default WatchlistPage
