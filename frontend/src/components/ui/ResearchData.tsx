import { useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
  const id = useId()
  const definition = useQuery({ queryKey: ['term', term], queryFn: () => api.getTermDefinition(term), enabled: open, staleTime: Infinity })
  const data = record(definition.data)
  return <span className="tooltip-wrapper" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false) }} onKeyDown={e => { if (e.key === 'Escape') setOpen(false) }}>
    <button type="button" className="term-trigger" aria-expanded={open} aria-controls={open ? id : undefined} onFocus={() => setOpen(true)} onClick={() => setOpen(true)}>{children ?? term}</button>
    {open && <span id={id} className="term-popover" role="note">
      <strong>{definition.data?.term ?? term}</strong>
      <DataStatus loading={definition.isLoading} error={definition.isError} label="definition" />
      {definition.data && <><span>{text(data.short_definition)}</span>{!!data.long_definition && <span>{text(data.long_definition)}</span>}<SourceLink url={data.external_reference_url}>Learn more — {text(data.reference_type, 'authoritative reference')}</SourceLink></>}
      <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)} aria-label={`Close ${term} definition`}>Close</button>
    </span>}
  </span>
}
