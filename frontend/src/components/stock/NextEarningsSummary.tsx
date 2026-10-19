import type { NextEarnings, NextEarningsEvidence } from '../../services/api'
import { record, SourceLink } from '../ui/ResearchData'
import { safeExternalUrl } from '../../utils/safeExternalUrl'
import './NextEarningsSummary.css'

// Navigation hygiene only: the backend owns official-origin/evidence validation.
function safeSourceLink(value: unknown): string | undefined {
  const href = safeExternalUrl(value)
  if (!href) return undefined
  const url = new URL(href), host = url.hostname.toLowerCase()
  if (url.protocol !== 'https:' || (url.port && url.port !== '443') || !host.includes('.') || host.includes(':') || /^[\d.]+$/.test(host) || /\.(?:local|localhost|internal|lan|home|home\.arpa|test|invalid)\.?$/.test(host) || host.endsWith('.')) return undefined
  return href
}

function timestamp(value: unknown): value is string {
  return typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value))
}

function evidenceValid(value: unknown): value is NextEarningsEvidence {
  const e = record(value), span = record(e.evidence_span)
  return ['event_id', 'source_document_id'].every(key => typeof e[key] === 'string' && !!e[key].trim()) && e.source === 'company_ir_rss' && !!safeSourceLink(e.source_url) && typeof e.source_content_hash === 'string' && /^[a-f\d]{64}$/i.test(e.source_content_hash) && timestamp(e.retrieved_at) && ['body', 'headline'].includes(String(span.field)) && Number.isInteger(span.start) && Number.isInteger(span.end) && Number(span.start) >= 0 && Number(span.end) > Number(span.start) && typeof span.text === 'string' && !!span.text.trim() && [...span.text].length === Number(span.end) - Number(span.start)
}

function confirmed(value: unknown, symbol: string): value is NextEarnings {
  const n = record(value)
  const date = typeof n.event_date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(n.event_date) ? new Date(`${n.event_date}T00:00:00Z`) : null
  return n.symbol === symbol && n.event_kind === 'results_release' && n.verification_status === 'verified' && n.verification_scope === 'explicit_official_announcement' && !!date && Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === n.event_date && !String(n.event_date).startsWith('0000') && ((n.session === 'unknown' && n.scheduled_time_precision === 'date') || (['bmo', 'amc'].includes(String(n.session)) && n.scheduled_time_precision === 'session')) && n.scheduled_at === null && n.event_timezone === null && n.countdown_basis === 'calendar_days' && Number.isSafeInteger(n.days_until) && Number(n.days_until) >= 0 && Array.isArray(n.evidence) && n.evidence.length > 0 && n.evidence.every(evidenceValid)
}

export function NextEarningsSummary({ symbol, nextEarnings, coverage, loading = false, error = false }: { symbol: string; nextEarnings?: unknown; coverage?: unknown; loading?: boolean; error?: boolean }) {
  const c = record(coverage)
  const conflict = c.confirmation_status === 'conflicting_announcements'
  const next = !loading && !error && !conflict && c.query_truncated !== true && confirmed(nextEarnings, symbol) ? nextEarnings : null
  let detail = 'Per-company source check unavailable; no confirmed date was supplied.'
  if (c.status === 'not_refreshed') detail = 'Official source has not been refreshed for this company.'
  if (c.status === 'checked' || c.status === 'empty') detail = timestamp(c.checked_at) ? 'Per-company source check recorded; no confirmed upcoming results date was supplied.' : 'Per-company source check time unavailable.'
  if (c.status === 'partial') detail = 'Official source coverage is incomplete.'
  if (c.status === 'error' || c.status === 'unavailable') detail = 'Official source check failed or is unavailable.'
  if (nextEarnings != null && !next && !conflict) detail = 'Announcement data could not be validated for display.'
  if (c.query_truncated === true) detail = 'Stored earnings coverage is incomplete; no date selected.'
  if (conflict) detail = 'Official announcements conflict; no date selected.'
  if (error) detail = 'Could not load next earnings information. This is not an unconfirmed-date result.'
  return <section className="next-earnings" aria-label="Next earnings" aria-busy={loading}>
    <div className="next-earnings__line">{loading ? <span role="status">Loading next earnings…</span> : error ? <span role="alert">Next earnings information could not be loaded.</span> : next ? <><strong>Next earnings results</strong><time dateTime={next.event_date}>{next.event_date}</time><span>{next.session === 'bmo' ? 'Before market open' : next.session === 'amc' ? 'After market close' : 'Time not confirmed'}</span><strong>{next.days_until === 0 ? 'Today' : `In ${next.days_until} calendar ${next.days_until === 1 ? 'day' : 'days'}`}</strong></> : <strong>Next earnings date not yet confirmed.</strong>}</div>
    {!loading && <details><summary>{next ? 'Retained official announcement · Source & evidence' : 'Earnings availability details'}</summary>
      {next && <><p>Saved official announcement; this page did not refresh or recheck the provider.</p>{next.evidence.map((e, i) => <div key={i}><SourceLink url={safeSourceLink(e.source_url)}>Official announcement</SourceLink><blockquote>{e.evidence_span.text}</blockquote><p>Retrieved: <time dateTime={e.retrieved_at}>{e.retrieved_at}</time></p></div>)}</>}
      <p>{next && !['not_refreshed', 'partial', 'error', 'unavailable'].includes(String(c.status)) ? 'Selection uses retained announcements only.' : detail}</p>
      {timestamp(c.checked_at) && <p>Per-company check recorded: <time dateTime={c.checked_at}>{c.checked_at}</time></p>}
    </details>}
  </section>
}
