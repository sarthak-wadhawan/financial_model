import { useId, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../services/api'
import { safeExternalUrl } from '../../utils/safeExternalUrl'

export function displayNumber(value: unknown, digits = 1): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits }) : 'Unavailable'
}

// Preserve date-only precision and the source's calendar date; never infer an event time.
export function displayDate(value: string | null | undefined): string {
  if (!value) return 'Date unavailable'
  const day = value.match(/^\d{4}-\d{2}-\d{2}/)?.[0]
  return day ?? value
}

export function eventDate(event: { scheduled_at?: string | null; released_at?: string | null; metadata?: Record<string, unknown> }): string | null {
  return event.released_at ?? event.scheduled_at ?? (typeof event.metadata?.event_date === 'string' ? event.metadata.event_date : null)
}

export function EventTiming({ event }: { event: { scheduled_at?: string | null; released_at?: string | null; metadata?: Record<string, unknown> } }) {
  const metadata = record(event.metadata)
  return <span>{displayDate(eventDate(event))}{!event.scheduled_at && !event.released_at && eventDate(event) ? ' · Exact time unknown' : ''}{metadata.session ? ` · Session: ${text(metadata.session)}` : ''}</span>
}

export function ProviderCoverage({ symbol }: { symbol?: string }) {
  const client = useQueryClient()
  const health = useQuery({ queryKey: ['providerCoverage'], queryFn: () => api.getProviderCoverage(), staleTime: 30000 })
  const refresh = useMutation({ mutationFn: () => api.refreshMarketData([symbol ?? 'AAPL']), onSuccess: async () => { await client.invalidateQueries() } })
  const providers = Object.entries(health.data?.providers ?? {})
  const counts = providers.reduce<Record<string, number>>((result, [, value]) => { const status = text(record(value).status, 'unknown'); result[status] = (result[status] ?? 0) + 1; return result }, {})
  return <section className="section provider-coverage" aria-label="Provider coverage"><h2>Provider coverage</h2><DataStatus loading={health.isLoading} error={health.isError} empty={health.isSuccess && !providers.length} label="provider coverage" /><p>{Object.entries(counts).map(([status, count]) => `${count} ${status}`).join(' · ')}</p><details><summary>Source status, refresh timestamps & coverage limits</summary><p>Coverage is the last server-wide refresh, not a guarantee of evidence for this company. Retained records may predate it. Empty sections do not establish that no event occurred.</p><ul>{providers.map(([name, value]) => { const state = record(value); return <li key={name}><strong>{name.replace(/_/g, ' ')}</strong>: {text(state.status, 'Unknown')} · Last refresh: {text(state.retrieved_at, 'Not refreshed')}{state.reason ? ` · ${text(state.reason)}` : ''}</li> })}</ul></details><button className="btn btn-secondary" disabled={refresh.isPending} onClick={() => refresh.mutate()}>{refresh.isPending ? 'Refreshing providers…' : `Refresh evidence for ${symbol ?? 'AAPL'}`}</button><p>Explicit bounded source refresh; may take a few minutes. Empty evidence may reflect incomplete coverage. No background monitoring.</p>{refresh.isError && <p role="alert">Refresh could not be confirmed. The server may still be working; check coverage before retrying.</p>}{refresh.isSuccess && <p role="status">Refresh request completed. Review each provider status; completion does not mean all sources succeeded.</p>}</section>
}

export function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export function text(value: unknown, fallback = 'Unavailable'): string {
  return typeof value === 'string' && value.length ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : typeof value === 'boolean' ? String(value) : fallback
}

export function SourceLink({ url, children = 'View source' }: { url: unknown; children?: React.ReactNode }) {
  const href = safeExternalUrl(url)
  return href ? <a className="link" href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children} — link unavailable</span>
}

export function DataStatus({ loading, error, empty, label }: { loading?: boolean; error?: boolean; empty?: boolean; label: string }) {
  if (!loading && !error && !empty) return null
  return <p className="data-status empty-state" role={error ? 'alert' : 'status'}>{loading ? `Loading ${label}…` : error ? `Could not load ${label}. Try again; this is not an empty result.` : `No ${label} available.`}</p>
}

export function Term({ term, children }: { term: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const touch = useRef(false)
  const id = useId()
  const definition = useQuery({ queryKey: ['term', term], queryFn: () => api.getTermDefinition(term), enabled: open, staleTime: Infinity })
  const data = record(definition.data)
  return <span className="tooltip-wrapper" onPointerDown={e => { touch.current = e.pointerType === 'touch' }} onTouchStart={() => { touch.current = true }} onMouseEnter={() => { if (!touch.current) setOpen(true) }} onMouseLeave={() => { if (!touch.current) setOpen(false) }} onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false) }} onKeyDown={e => { if (e.key === 'Escape') setOpen(false) }}>
    <button type="button" className="term-trigger" aria-expanded={open} aria-controls={open ? id : undefined} onFocus={() => setOpen(true)} onClick={() => setOpen(true)}>{children ?? term}</button>
    {open && <span id={id} className="term-popover" role="note">
      <strong>{definition.data?.term ?? term}</strong>
      <DataStatus loading={definition.isLoading} error={definition.isError} label="definition" />
      {definition.data && <><span>{text(data.short_definition)}</span>{!!data.long_definition && <span>{text(data.long_definition)}</span>}<SourceLink url={data.external_reference_url}>Learn more — {text(data.reference_type, 'authoritative reference')}</SourceLink></>}
      <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)} aria-label={`Close ${term} definition`}>Close</button>
    </span>}
  </span>
}
