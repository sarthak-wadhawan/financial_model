import { useParams } from 'react-router-dom'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import type { Interpretation } from '../services/api'
import { Badge } from '../components/ui'
import { DataStatus, displayDate, displayNumber, record, SourceLink, Term, text } from '../components/ui/ResearchData'

const tabs = ['overview', 'earnings', 'events', 'news', 'insiders', 'leadership', 'filings', 'quant']

export function StockPage() {
  const { symbol: routeSymbol } = useParams<{ symbol: string }>()
  const symbol = routeSymbol?.toUpperCase() ?? ''
  const [activeTab, setActiveTab] = useState('overview')
  const detail = useQuery({ queryKey: ['stockDetail', symbol], queryFn: () => api.getStockDetail(symbol), enabled: !!symbol })
  const interpretation = useQuery({ queryKey: ['interpretation', symbol], queryFn: () => api.getInterpretation(symbol), enabled: !!symbol })
  const bars = useQuery({ queryKey: ['stockBars', symbol], queryFn: () => api.getBars(symbol, '1Day', undefined, undefined, 20), enabled: !!symbol })
  const section = useQuery<unknown>({ queryKey: ['stockSection', symbol, activeTab], enabled: !!symbol && activeTab !== 'overview', queryFn: () => {
    switch (activeTab) {
      case 'earnings': return api.getEarnings(symbol)
      case 'events': return api.getEvents(symbol, undefined, 50)
      case 'news': return api.getNews(symbol, 20)
      case 'insiders': return api.getInsiders(symbol, 50)
      case 'leadership': return api.getLeadership(symbol)
      case 'filings': return api.getFilings(symbol, 20)
      default: return api.getQuantSignals(symbol)
    }
  } })
  const stock = record(detail.data), priceData = record(stock.price_data)
  const history = record(bars.data)
  if (!symbol) return <div className="empty-state">No symbol specified.</div>
  return <div className="stock-page">
    <div className="stock-header"><div className="stock-header-main"><div className="stock-identity"><h1>{symbol}</h1><span className="stock-exchange">{text(stock.name, 'Company name unavailable')} · {text(stock.exchange, 'Exchange unavailable')}</span></div><div className="stock-price"><span className="current-price">{typeof stock.price === 'number' ? `$${displayNumber(stock.price, 2)}` : 'Price unavailable'}</span><span className="price-change neutral">Daily change: {typeof stock.change_pct === 'number' ? `${displayNumber(stock.change_pct, 2)}%` : 'Unavailable'}</span></div></div>
      <DataStatus loading={detail.isLoading} error={detail.isError} label="company details and daily close" />
      <p className="data-status">Latest completed daily close, not a live quote. <Provenance data={priceData} /></p>
      <nav className="stock-tabs" role="tablist" aria-label="Stock sections">{tabs.map(tab => <button key={tab} type="button" role="tab" id={`stock-tab-${tab}`} aria-controls="stock-panel" aria-selected={activeTab === tab} tabIndex={activeTab === tab ? 0 : -1} className={`tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)} onKeyDown={e => {
        const i = tabs.indexOf(tab)
        const next = e.key === 'ArrowRight' ? tabs[(i + 1) % tabs.length] : e.key === 'ArrowLeft' ? tabs[(i + tabs.length - 1) % tabs.length] : e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[tabs.length - 1] : null
        if (next) { e.preventDefault(); setActiveTab(next); document.getElementById(`stock-tab-${next}`)?.focus() }
      }}>{tab.charAt(0).toUpperCase() + tab.slice(1)}</button>)}</nav>
    </div>
    <div className="stock-content" id="stock-panel" role="tabpanel" aria-labelledby={`stock-tab-${activeTab}`} tabIndex={0}>
      {activeTab === 'overview' ? <>
        <DataStatus loading={interpretation.isLoading} error={interpretation.isError} empty={interpretation.isSuccess && !interpretation.data} label="Phase 9 interpretation" />
        {interpretation.data && <Overview interpretation={interpretation.data} />}
        <details className="section price-history"><summary>Price history — provider bars</summary><p className="data-status"><Provenance data={history} /></p><DataStatus loading={bars.isLoading} error={bars.isError} empty={bars.isSuccess && !bars.data?.bars?.length} label="price bars; no chart is inferred from missing data" />{!!bars.data?.bars?.length && <><PriceChart bars={bars.data.bars} /><div className="table-container" tabIndex={0} role="region" aria-label="Daily price history"><table><caption>Daily closes; source calendar dates</caption><thead><tr><th scope="col">Date</th><th scope="col">Close</th><th scope="col">Volume</th></tr></thead><tbody>{bars.data.bars.map(bar => <tr key={bar.t}><td>{displayDate(bar.t)}</td><td>{displayNumber(bar.c, 2)}</td><td>{displayNumber(bar.v, 0)}</td></tr>)}</tbody></table></div></>}</details>
        <AnswerForm key={symbol} symbol={symbol} />
      </> : <>
        <DataStatus loading={section.isLoading} error={section.isError} label={`${activeTab} data`} />
        {section.isError && <button className="btn btn-secondary" onClick={() => section.refetch()}>Retry {activeTab}</button>}
        {section.isSuccess && (activeTab === 'leadership' ? <Leadership data={section.data} /> : activeTab === 'quant' ? <Quant data={section.data} /> : <EventList data={section.data} label={activeTab} />)}
      </>}
    </div>
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
    return <article key={text(event.event_id, String(n))} className="event-item"><div className="event-info"><h3>{text(event.title)}</h3><p>{text(event.description, 'Description unavailable')}</p><p className="event-meta">{text(event.event_type)} · {text(event.status)} · {text(event.importance)}</p><p>Scheduled date: {displayDate(typeof event.scheduled_at === 'string' ? event.scheduled_at : null)} · Publication date: {displayDate(typeof event.released_at === 'string' ? event.released_at : null)}</p><p className="event-source">Source: {text(event.source)}{/(test|fixture|mock|demo)/i.test(text(event.source)) ? ' — test/demo provenance, not live evidence' : ''}</p><SourceLink url={event.source_url} /><details><summary>Provider fields & provenance</summary><p>Event ID: {text(event.event_id)} · Source ID: {text(event.source_id)}</p><p>First seen: {displayDate(typeof event.first_seen_at === 'string' ? event.first_seen_at : null)} · Last seen: {displayDate(typeof event.last_seen_at === 'string' ? event.last_seen_at : null)}</p><dl>{Object.entries(metadata).map(([key, field]) => <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{typeof field === 'object' && field !== null ? JSON.stringify(field) : text(field, 'Unknown')}</dd></div>)}</dl></details></div></article>
  })}</div></div>
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

function PriceChart({ bars }: { bars: Array<{ t: string; c: number }> }) {
  const valid = bars.filter(bar => Number.isFinite(bar.c)).slice().sort((a, b) => a.t.localeCompare(b.t))
  if (valid.length < 2) return <p>At least two valid daily closes are required for a chart.</p>
  const low = Math.min(...valid.map(bar => bar.c)), high = Math.max(...valid.map(bar => bar.c))
  const points = valid.map((bar, n) => `${10 + n / (valid.length - 1) * 580},${high === low ? 80 : 150 - (bar.c - low) / (high - low) * 140}`).join(' ')
  return <figure className="price-history"><figcaption>Daily closing prices, {displayDate(valid[0].t)} to {displayDate(valid[valid.length - 1].t)}. Range ${displayNumber(low, 2)}–${displayNumber(high, 2)}; exact values in the table below.</figcaption><svg width="100%" height="160" viewBox="0 0 600 160" role="img" aria-label="Provider-supplied daily closing price history"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" /></svg></figure>
}
export default StockPage
