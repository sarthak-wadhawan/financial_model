import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { NextEarnings } from '../../services/api'
import { NextEarningsSummary } from './NextEarningsSummary'

const announcement: NextEarnings = {
  symbol: 'V', event_kind: 'results_release', event_date: '2026-10-27', session: 'amc', scheduled_time_precision: 'session', scheduled_at: null, event_timezone: null,
  days_until: 11, countdown_basis: 'calendar_days', fiscal_period: 'fourth:2026', verification_status: 'verified', verification_scope: 'explicit_official_announcement', event_ids: ['saved-event'],
  evidence: [{ event_id: 'saved-event', source: 'company_ir_rss', source_url: 'https://investor.visa.com/announcement', source_document_id: 'saved-document', source_content_hash: 'a'.repeat(64), retrieved_at: '2026-10-16T12:00:00+00:00', evidence_span: { field: 'body', start: 0, end: 23, text: 'Official saved evidence' } }],
}
const coverage = { status: 'not_refreshed', confirmation_status: 'retained_official_announcement', checked_at: null, selection_scope: 'retained_events_only', query_truncated: false }
function mount(nextEarnings: unknown = announcement, extra = {}) {
  return render(<NextEarningsSummary symbol="V" nextEarnings={nextEarnings} coverage={coverage} {...extra} />)
}

describe('NextEarningsSummary retained server projection', () => {
  it('renders calendar date/session/countdown, with accessible saved evidence and no fabricated clock', () => {
    mount()
    expect(screen.getByText('2026-10-27')).toHaveAttribute('dateTime', '2026-10-27')
    expect(screen.getByText('After market close')).toBeVisible()
    expect(screen.getByText('In 11 calendar days')).toBeVisible()
    const disclosure = screen.getByText('Retained official announcement · Source & evidence')
    expect(disclosure.closest('details')).not.toHaveAttribute('open')
    fireEvent.click(disclosure)
    expect(screen.getByRole('link', { name: 'Official announcement' })).toHaveAttribute('href', announcement.evidence[0].source_url)
    expect(screen.getByText('Official saved evidence')).toBeVisible()
    expect(screen.getByText(announcement.evidence[0].retrieved_at)).toBeVisible()
    expect(screen.getByText(/this page did not refresh or recheck/)).toBeVisible()
    expect(screen.queryByText(/09:30|16:00|T00:00|saved-document|saved-event/)).not.toBeInTheDocument()
  })
  it.each(['bmo', 'unknown'] as const)('supports %s without inventing a release time', session => {
    mount({ ...announcement, session, scheduled_time_precision: session === 'unknown' ? 'date' : 'session', days_until: 0 })
    expect(screen.getByText(session === 'bmo' ? 'Before market open' : 'Time not confirmed')).toBeVisible()
    expect(screen.getByText('Today')).toBeVisible()
  })
  it.each([
    { symbol: 'TMO' }, { event_kind: 'earnings_call' }, { verification_status: 'unverified' }, { verification_scope: 'estimate' },
    { event_date: '2026-02-30' }, { event_date: '2026-10-27T00:00:00Z' }, { session: 'amc', scheduled_time_precision: 'date' },
    { scheduled_at: '2026-10-27T16:00:00Z' }, { event_timezone: 'UTC' }, { days_until: -1 }, { days_until: 1.5 }, { countdown_basis: 'hours' }, { evidence: [] }, { evidence: [null] },
    { evidence: [{ ...announcement.evidence[0], retrieved_at: 'invalid' }] }, { evidence: [{ ...announcement.evidence[0], evidence_span: {} }] },
  ])('fails closed for malformed/unverified projection %j', patch => {
    mount({ ...announcement, ...patch })
    expect(screen.getByText('Next earnings date not yet confirmed.')).toBeVisible()
    expect(screen.queryByText('2026-10-27')).not.toBeInTheDocument()
  })
  it.each(['javascript:alert(1)', 'https://127.0.0.1/a', 'https://10.0.0.1/a', 'https://[::1]/a', 'https://localhost/a', 'https://service.internal/a', 'https://user:password@investor.visa.com/a', 'http://investor.visa.com/a'])('rejects unsafe navigation %s', source_url => {
    mount({ ...announcement, evidence: [{ ...announcement.evidence[0], source_url }] })
    expect(screen.getByText('Next earnings date not yet confirmed.')).toBeVisible()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
  it('suppresses conflicting announcements even if a projection is supplied', () => {
    mount(announcement, { coverage: { ...coverage, confirmation_status: 'conflicting_announcements' } })
    expect(screen.getByText('Next earnings date not yet confirmed.')).toBeVisible()
    fireEvent.click(screen.getByText('Earnings availability details'))
    expect(screen.getByText('Official announcements conflict; no date selected.')).toBeVisible()
  })
  it.each([
    ['not_refreshed', 'Official source has not been refreshed for this company.'],
    ['error', 'Official source check failed or is unavailable.'],
    ['partial', 'Official source coverage is incomplete.'],
  ])('explains %s without claiming global checked-empty coverage', (status, message) => {
    mount(null, { coverage: { ...coverage, status } })
    expect(screen.getAllByText('Next earnings date not yet confirmed.')).toHaveLength(1)
    fireEvent.click(screen.getByText('Earnings availability details'))
    expect(screen.getByText(message)).toBeVisible()
    expect(screen.queryByText(/checked.*empty/i)).not.toBeInTheDocument()
  })
  it('distinguishes request failure from unconfirmed, and suppresses stale dates', () => {
    mount(announcement, { error: true })
    expect(screen.getByRole('alert')).toHaveTextContent('Next earnings information could not be loaded.')
    expect(screen.queryByText('Next earnings date not yet confirmed.')).not.toBeInTheDocument()
    expect(screen.queryByText('2026-10-27')).not.toBeInTheDocument()
  })
  it('does not turn global provider state into a per-company checked-empty claim', () => {
    mount(null, { coverage: { status: 'empty', checked_at: null } })
    fireEvent.click(screen.getByText('Earnings availability details'))
    expect(screen.getByText('Per-company source check time unavailable.')).toBeVisible()
    expect(screen.queryByText(/source check recorded/)).not.toBeInTheDocument()
  })
  it('keeps a failed source check distinct from valid retained evidence', () => {
    mount(announcement, { coverage: { ...coverage, status: 'error' } })
    expect(screen.getByText('2026-10-27')).toBeVisible()
    fireEvent.click(screen.getByText('Retained official announcement · Source & evidence'))
    expect(screen.getByText('Official source check failed or is unavailable.')).toBeVisible()
  })
  it('distinguishes loading from unconfirmed', () => {
    mount(undefined, { loading: true })
    expect(screen.getByRole('status')).toHaveTextContent('Loading next earnings…')
    expect(screen.queryByText('Next earnings date not yet confirmed.')).not.toBeInTheDocument()
  })
})
