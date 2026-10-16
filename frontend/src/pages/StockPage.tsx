import { useParams } from 'react-router-dom'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import type { Interpretation } from '../services/api'
import { Badge } from '../components/ui'
import { PriceHistoryChart } from '../components/stock/PriceHistoryChart'
import './StockPage.css'
import { DataStatus, displayDate, displayNumber, EventTiming, ProviderCoverage, record, SourceLink, Term, text } from '../components/ui/ResearchData'

const tabs = ['overview', 'earnings', 'events', 'news', 'management', 'insiders', 'leadership', 'filings', 'quant']

export function StockPage() {
  const { symbol: routeSymbol } = useParams<{ symbol: string }>()
  const symbol = routeSymbol?.toUpperCase() ?? ''
  const [activeTab, setActiveTab] = useState('overview')
  const detail = useQuery({ queryKey: ['stockDetail', symbol], queryFn: () => api.getStockDetail(symbol), enabled: !!symbol })
  const interpretation = useQuery({ queryKey: ['interpretation', symbol], queryFn: () => api.getInterpretation(symbol), enabled: !!symbol })
  const section = useQuery<unknown>({ queryKey: ['stockSection', symbol, activeTab], enabled: !!symbol && activeTab !== 'overview', queryFn: () => {
    switch (activeTab) {
      case 'earnings': return api.getEarnings(symbol)
      case 'events': return api.getEvents(symbol, undefined, 50)
      case 'management': return api.getEvents(symbol, undefined, 100)
      case 'news': return api.getNews(symbol, 20)
      case 'insiders': return api.getInsiders(symbol, 50)
      case 'leadership': return api.getLeadership(symbol)
      case 'filings': return api.getFilings(symbol, 20)
      default: return api.getQuantSignals(symbol)
    }
  } })
  const stock = record(detail.data), priceData = record(stock.price_data)
  const identity = record(stock.identity)
  const change = finite(stock.change), changePct = finite(stock.change_pct)
  const direction = change ?? changePct
  const changeStyle = direction === null || direction === 0 ? 'neutral' : direction > 0 ? 'positive' : 'negative'
  const scheduledResults = (detail.data?.events ?? []).filter(event => {
    const metadata = record(event.metadata)
    const date = event.scheduled_at ?? (typeof metadata.event_date === 'string' ? metadata.event_date : null)
    return event.event_type === 'earnings' && event.status === 'scheduled' && !event.released_at && !metadata.is_estimate && !metadata.estimated && !/(call|conference|webcast)/i.test(`${event.title} ${text(metadata.event_subtype, '')}`) && !!date && Number.isFinite(Date.parse(date)) && date.slice(0, 10) >= new Date().toISOString().slice(0, 10)
  }).sort((a, b) => text(a.scheduled_at ?? record(a.metadata).event_date).localeCompare(text(b.scheduled_at ?? record(b.metadata).event_date)))
  const nextResults = scheduledResults[0]
  if (!symbol) return <div className="empty-state">No symbol specified.</div>
  return <div className="stock-page">
    <div className="stock-header"><div className="stock-header-main"><div className="stock-identity"><h1>{text(stock.name, symbol)}</h1><span className="stock-exchange">{symbol} · {text(stock.exchange, 'Exchange unavailable')}</span>{detail.isSuccess && !stock.name && <p className="data-status">Company name unavailable</p>}</div><div className="stock-price"><span className="current-price">{finite(stock.price) !== null ? `$${displayNumber(stock.price, 2)}` : 'Price unavailable'}</span><span className={`price-change ${changeStyle}`}>Daily change: {change === null ? 'Unavailable' : signedChange(change, '$')} ({changePct === null ? 'Unavailable' : signedChange(changePct, '%')})</span></div></div>
      <DataStatus loading={detail.isLoading} error={detail.isError} label="company details and daily close" />
      <p className="data-status">Latest completed daily close, not a live quote. {displayDate(typeof priceData.market_timestamp === 'string' ? priceData.market_timestamp : null)} · Source: {text(priceData.source)}{priceData.mode === 'demo' ? ' · Demo/test data' : ''}</p>
      <p className="stock-next-earnings">{nextResults ? <>Next scheduled earnings results: <EventTiming event={nextResults} /> · Source: {nextResults.source} <SourceLink url={nextResults.source_url} /></> : 'Next earnings date not yet confirmed'}</p>
      {!!Object.keys(identity).length && <p className="data-status">Company identity: {text(identity.source)} · Verified as of {displayDate(typeof identity.verified_as_of === 'string' ? identity.verified_as_of : null)} · {text(identity.status, 'Status unavailable')}</p>}
      <details className="stock-diagnostics"><summary>Price & identity provenance</summary><p><Provenance data={priceData} /></p>{!!Object.keys(identity).length && <><p>Identity source: {text(identity.source)} · Retrieved: {text(identity.retrieved_at)} · Status: {text(identity.status)}{identity.reason ? ` · ${text(identity.reason)}` : ''}</p><SourceLink url={identity.source_url}>Identity source</SourceLink></>}</details>
      <nav className="stock-tabs" role="tablist" aria-label="Stock sections">{tabs.map(tab => <button key={tab} type="button" role="tab" id={`stock-tab-${tab}`} aria-controls="stock-panel" aria-selected={activeTab === tab} tabIndex={activeTab === tab ? 0 : -1} className={`tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)} onKeyDown={e => {
        const i = tabs.indexOf(tab)
        const next = e.key === 'ArrowRight' ? tabs[(i + 1) % tabs.length] : e.key === 'ArrowLeft' ? tabs[(i + tabs.length - 1) % tabs.length] : e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[tabs.length - 1] : null
        if (next) { e.preventDefault(); setActiveTab(next); document.getElementById(`stock-tab-${next}`)?.focus() }
      }}>{tab.charAt(0).toUpperCase() + tab.slice(1)}</button>)}</nav>
    </div>
    <div className="stock-content" id="stock-panel" role="tabpanel" aria-labelledby={`stock-tab-${activeTab}`} tabIndex={0}>
      {activeTab === 'overview' ? <>
        <PriceHistoryChart symbol={symbol} />
        <DataStatus loading={interpretation.isLoading} error={interpretation.isError} empty={interpretation.isSuccess && !interpretation.data} label="Phase 9 interpretation" />
        {interpretation.data && <Overview interpretation={interpretation.data} />}
        <AnswerForm key={symbol} symbol={symbol} />
      </> : <>
        <DataStatus loading={section.isLoading} error={section.isError} label={`${activeTab} data`} />
        {section.isError && <button className="btn btn-secondary" onClick={() => section.refetch()}>Retry {activeTab}</button>}
        {section.isSuccess && (activeTab === 'management' ? <Management data={section.data} /> : activeTab === 'leadership' ? <Leadership data={section.data} /> : activeTab === 'quant' ? <Quant data={section.data} /> : <EventList data={section.data} label={activeTab} />)}
      </>}
    </div>
    <details className="stock-diagnostics"><summary>Provider diagnostics & coverage</summary><ProviderCoverage key={symbol} symbol={symbol} /></details>
  </div>
}

function Overview({ interpretation: i }: { interpretation: Interpretation }) {
  return <div className="tab-content overview-tab">
    <section className="section what-you-need-to-know"><h2>What You Need to Know</h2><p className="data-status">Deterministic Phase 9 interpretation · As of {displayDate(i.as_of)} · Not a trading instruction.</p><p>Learn the terms: <Term term="guidance">Guidance</Term> · <Term term="EPS">EPS</Term> · <Term term="volatility">Volatility</Term></p><div className="key-points">{[['Headline', i.headline], ['What Happened', i.what_happened], ['What It Means', i.what_it_means], ['Why It Matters', i.why_it_matters]].map(([label, value]) => <div className="key-point" key={label}><h3 className="kp-label">{label}</h3><p className="kp-value">{value || 'Unavailable'}</p></div>)}</div></section>
    <section className="section impact-section"><h2>Company ≠ stock impact</h2><div className="impact-grid">
      <Impact title="Company Impact" data={record(i.company_impact)} direction={i.company_impact?.direction} />
      <Impact title="Stock Impact" data={record(i.stock_impact)} direction={i.stock_impact?.bias} />
    </div></section>
    <section className="section scenarios-section"><h2>Scenario Analysis</h2><p>Conditional views, not price forecasts. Any probability band comes from Phase 9, not an estimate by this page.</p><div className="scenarios-grid">{[['base', i.base_case], ['bull', i.bull_case], ['bear', i.bear_case]].map(([variant, scenario]) => <Scenario key={String(variant)} variant={String(variant)} data={record(scenario)} />)}</div></section>
    <section className="section view-change-section"><h2>What Would Change the View?</h2><div className="triggers-list">{i.what_would_change_view?.map((trigger, n) => <div className="trigger-item" key={n}><strong>{trigger.trigger}</strong><p>{trigger.description}</p></div>)}</div>{!i.what_would_change_view?.length && <p>No change-view conditions supplied.</p>}</section>
    <details className="section confidence-section" open><summary>Confidence & missing information</summary><div className="confidence-display"><p className="confidence-score">Confidence: {confidence(i.confidence)}</p><ul className="confidence-factors">{i.confidence_reasons?.map((reason, n) => <li key={n}>{reason}</li>)}</ul><div className="missing-info"><h3>Missing Information</h3><ul>{i.missing_information?.map((missing, n) => <li key={n}>{missing}</li>)}</ul>{!i.missing_information?.length && <p>No missing-information flags supplied; this does not guarantee complete coverage.</p>}</div></div></details>
    <details className="section evidence-section"><summary>Supporting Evidence ({i.supporting_evidence?.length ?? 0})</summary><DataStatus empty={!i.supporting_evidence?.length} label="supporting evidence references" /><div className="evidence-list">{i.supporting_evidence?.map((evidence, n) => <Evidence key={n} data={record(evidence)} />)}</div></details>
  </div>
}

function Impact({ title, data, direction }: { title: string; data: Record<string, unknown>; direction: unknown }) {
  const variant = direction === 'positive' || direction === 'bullish' ? 'success' : direction === 'negative' || direction === 'bearish' ? 'error' : direction === 'mixed' ? 'warning' : 'default'
  return <article className={`impact-card ${title === 'Company Impact' ? 'company-impact' : 'stock-impact'}`}><h3>{title}</h3><Badge variant={variant}>{text(direction, 'Unknown')}</Badge><p>Magnitude: {text(data.magnitude, 'Unknown')}</p><p>Time horizon: {text(data.horizon, 'Unknown')}</p><p>Confidence: {confidence(data.confidence)}</p><ul className="reasons-list">{Array.isArray(data.reasons) && data.reasons.map((reason, n) => <li key={n}>{text(reason)}</li>)}</ul></article>
}

function Scenario({ variant, data }: { variant: string; data: Record<string, unknown> }) {
  return <article className={`scenario-card scenario-${variant}`}><h3 className="scenario-label">{variant.toUpperCase()} CASE</h3><p className="scenario-description">{text(data.description, 'Scenario unavailable')}</p>{data.probability_band != null && <p className="probability">Backend probability band: {text(data.probability_band)}</p>}<details className="scenario-conditions"><summary>Required conditions</summary><ul>{Array.isArray(data.required_conditions) && data.required_conditions.map((condition, n) => <li key={n}>{text(condition)}</li>)}</ul>{(!Array.isArray(data.required_conditions) || !data.required_conditions.length) && <p>Conditions unavailable.</p>}</details></article>
}

function Evidence({ data }: { data: Record<string, unknown> }) {
  return <article className="evidence-item"><span className="evidence-source">{text(data.source_type, 'Source type unavailable')}</span><p>{text(data.description)}</p><SourceLink url={data.url} /><span className="evidence-time">Evidence date: {displayDate(typeof data.timestamp === 'string' ? data.timestamp : null)}</span>{!!data.evidence_id && <small>Evidence ID: {text(data.evidence_id)}</small>}</article>
}

function Provenance({ data }: { data: Record<string, unknown> }) {
  return <span>Mode: {text(data.mode, 'Not supplied')} · Source: {text(data.source)} · Market timestamp (as supplied): {text(data.market_timestamp)} · Retrieval timestamp (as supplied): {text(data.retrieved_at)}{data.status ? ` · Status: ${text(data.status)}` : ''}{data.reason ? ` · ${text(data.reason)}` : ''}</span>
}

function EventList({ data, label }: { data: unknown; label: string }) {
  const events = Array.isArray(data) ? data : []
  return <div className={`tab-content ${label}-tab`}><h2>{label.charAt(0).toUpperCase() + label.slice(1)} evidence</h2><DataStatus empty={!events.length} label={`${label} records`} /><div className="events-list">{events.map((value, n) => {
    const event = record(value), metadata = record(event.metadata)
    return <article key={text(event.event_id, String(n))} className="event-item"><div className="event-info"><h3>{text(event.title)}</h3><p>{text(event.description, 'Description unavailable')}</p><p className="event-meta">{text(event.event_type)} · {text(event.status)} · {text(event.importance)}</p><p>Event date: <EventTiming event={{ scheduled_at: typeof event.scheduled_at === 'string' ? event.scheduled_at : null, released_at: typeof event.released_at === 'string' ? event.released_at : null, metadata }} /></p><p className="event-source">Source: {text(event.source)}{/(test|fixture|mock|demo)/i.test(text(event.source)) ? ' — test/demo provenance, not live evidence' : ''}</p><SourceLink url={event.source_url} /><details><summary>Provider fields & provenance</summary><p>Event ID: {text(event.event_id)} · Source ID: {text(event.source_id)}</p><p>First seen: {displayDate(typeof event.first_seen_at === 'string' ? event.first_seen_at : null)} · Last seen: {displayDate(typeof event.last_seen_at === 'string' ? event.last_seen_at : null)}</p><dl>{Object.entries(metadata).map(([key, field]) => <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{typeof field === 'object' && field !== null ? JSON.stringify(field) : text(field, 'Unknown')}</dd></div>)}</dl></details></div></article>
  })}</div></div>
}

function Management({ data }: { data: unknown }) {
  const statements = (Array.isArray(data) ? data : []).flatMap(value => {
    const event = record(value), metadata = record(event.metadata)
    return (Array.isArray(metadata.management_statements) ? metadata.management_statements : []).map(value => ({ statement: record(value), event }))
  })
  return <section className="section management-tab"><h2>Management statements</h2><p>Attributed source statements, not independently verified outcomes. Showing extracted statements from up to 100 retained events; no statements does not mean management made none.</p><DataStatus empty={!statements.length} label="extracted management statements" />{statements.map(({ statement: s, event }, n) => <article className="evidence-item" key={text(s.statement_id, String(n))}><h3>{text(s.speaker, 'Speaker unavailable')} · {text(s.speaker_role, 'Role unavailable')}</h3><p>{text(s.statement)}</p><p>Category: {text(s.statement_type)} · Extraction: {text(s.extraction_method)} · Confidence: {confidence(s.confidence)}</p><h4>Exact source evidence</h4><blockquote>{text(record(s.evidence_span).text, 'Exact evidence unavailable')}</blockquote><p>Statement date: {displayDate(typeof s.event_date === 'string' ? s.event_date : null)} · Publication / filing timestamp (as supplied): {text(s.published_at)} · Retrieved: {text(s.retrieved_at)}</p><p>Source: {text(s.source_type, text(event.source))} · Document: {text(s.source_document_id)} · Event: {text(event.event_id)}</p><SourceLink url={s.source_url ?? event.source_url} /></article>)}</section>
}

function Leadership({ data }: { data: unknown }) {
  const leaders = record(record(data).leadership)
  return <div className="tab-content leadership-tab"><h2>Evidence-derived leadership</h2><DataStatus empty={!Object.keys(leaders).length} label="leadership records" /><div className="leadership-grid">{Object.entries(leaders).map(([role, value]) => { const leader = record(value); return <article key={role} className="leader-card"><h3>{role.toUpperCase()}</h3><p className="leader-name">{text(leader.name)}</p><p>Effective date: {displayDate(typeof leader.effective_date === 'string' ? leader.effective_date : null)}</p><p>Source: {text(leader.source)} · Event: {text(leader.event_id)}</p><SourceLink url={leader.source_url} /></article> })}</div></div>
}

function Quant({ data }: { data: unknown }) {
  const quant = record(data), signals = record(quant.signals)
  return <div className="tab-content quant-tab"><h2>Quant Signals</h2><p className="data-status"><Provenance data={quant} /></p><p>Score: {displayNumber(quant.quant_score)} · Rank: {text(quant.rank)} · Calculation date: {displayDate(typeof quant.calculated_at === 'string' ? quant.calculated_at : null)}</p><DataStatus empty={!Object.keys(signals).length} label="quant signals" /><div className="signals-grid">{Object.entries(signals).map(([name, value]) => <article className="signal-card" key={name}><h3 className="signal-name">{name.replace(/_/g, ' ')}</h3><span className="signal-value">{displayNumber(value, 2)}</span></article>)}</div><details><summary>Backend score components</summary><dl>{Object.entries(record(quant.components)).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{displayNumber(value, 2)}</dd></div>)}</dl></details></div>
}

function AnswerForm({ symbol }: { symbol: string }) {
  const [question, setQuestion] = useState('')
  const answer = useMutation({ mutationFn: (value: string) => api.answerQuestion(symbol, value) })
  const data = record(answer.data)
  return <section className="section"><h2>Ask about {symbol}</h2><p>Evidence-backed, deterministic answers. Missing evidence remains missing.</p><form className="search-form" onSubmit={e => { e.preventDefault(); if (question.trim()) answer.mutate(question.trim()) }}><label htmlFor="stock-question">Research question</label><input className="search-input" id="stock-question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="What would change the view?" maxLength={1000} /><button className="btn btn-primary" disabled={!question.trim() || answer.isPending}>Ask</button></form><DataStatus loading={answer.isPending} error={answer.isError} label="answer" />{answer.isSuccess && <article><h3>{text(data.question)}</h3><p>{text(data.answer)}</p><p>Confidence: {confidence(data.confidence)}</p><details><summary>Answer evidence</summary>{Array.isArray(data.evidence_refs) && data.evidence_refs.map((evidence, n) => <Evidence key={n} data={record(evidence)} />)}</details></article>}</section>
}

function confidence(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(0)}%` : 'Unavailable'
}

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function signedChange(value: number, unit: '$' | '%'): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return unit === '$' ? `${sign}$${displayNumber(Math.abs(value), 2)}` : `${sign}${displayNumber(Math.abs(value), 2)}%`
}
export default StockPage
