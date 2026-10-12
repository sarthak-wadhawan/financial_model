import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { api } from '../services/api'
import type {
  Interpretation,
  EarningsEvent,
  CompanyEvent,
  NewsEvent,
  InsiderTransaction,
  LeadershipData,
  Filing,
  QuantSignals,
} from '../services/api'
import {
  SkeletonCard,
  SkeletonText,
} from '../components/ui/LoadingSpinner'
import { Badge } from '../components/ui'

export function StockPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: interpretation, isLoading: interpLoading } = useQuery({
    queryKey: ['interpretation', symbol],
    queryFn: () => api.getInterpretation(symbol!),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })

  const { data: earnings, isLoading: earningsLoading } = useQuery({
    queryKey: ['earnings', symbol],
    queryFn: () => api.getEarnings(symbol!),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })

  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ['events', symbol],
    queryFn: () => api.getEvents(symbol!, undefined, 50),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })

  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: ['news', symbol],
    queryFn: () => api.getNews(symbol!, 20),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })

  const { data: insiders, isLoading: insidersLoading } = useQuery({
    queryKey: ['insiders', symbol],
    queryFn: () => api.getInsiders(symbol!, 50),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 60,
  })

  const { data: leadership, isLoading: leadershipLoading } = useQuery({
    queryKey: ['leadership', symbol],
    queryFn: () => api.getLeadership(symbol!),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 60,
  })

  const { data: filings, isLoading: filingsLoading } = useQuery({
    queryKey: ['filings', symbol],
    queryFn: () => api.getFilings(symbol!, 20),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 60,
  })

  const { data: quant, isLoading: quantLoading } = useQuery({
    queryKey: ['quant', symbol],
    queryFn: () => api.getQuantSignals(symbol!),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })

  if (!symbol) return <div>No symbol specified</div>

  return (
    <div className="stock-page">
      <div className="stock-header">
        <div className="stock-header-main">
          <div className="stock-identity">
            <h1>{symbol.toUpperCase()}</h1>
            <span className="stock-exchange">NASDAQ</span>
          </div>
          <div className="stock-price">
            <span className="current-price">$-</span>
            <span className="price-change neutral">-</span>
          </div>
        </div>
        <div className="stock-nav">
          <nav className="stock-tabs" role="tablist" aria-label="Stock sections">
            {['overview', 'earnings', 'events', 'news', 'insiders', 'leadership', 'filings', 'quant'].map((tab) => {
              return (
                <button
                  key={tab}
                  role="tab"
                  aria-selected={activeTab === tab}
                  onClick={() => setActiveTab(tab)}
                  className={`tab ${activeTab === tab ? 'active' : ''}`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      <main className="stock-content">
        {activeTab === 'overview' && <OverviewTab interpretation={interpretation} loading={interpLoading} />}
        {activeTab === 'earnings' && <EarningsTab earnings={earnings} loading={earningsLoading} />}
        {activeTab === 'events' && <EventsTab events={events} loading={eventsLoading} />}
        {activeTab === 'news' && <NewsTab news={news} loading={newsLoading} />}
        {activeTab === 'insiders' && <InsidersTab insiders={insiders} loading={insidersLoading} />}
        {activeTab === 'leadership' && <LeadershipTab leadership={leadership} loading={leadershipLoading} />}
        {activeTab === 'filings' && <FilingsTab filings={filings} loading={filingsLoading} />}
        {activeTab === 'quant' && <QuantTab quant={quant} loading={quantLoading} />}
      </main>
    </div>
  )
}

function OverviewTab({ interpretation, loading }: { interpretation: Interpretation | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><div className="skeleton-card" /><div className="skeleton-card" /></div>

  if (!interpretation) return <div className="empty-state">No interpretation available</div>

  return (
    <div className="tab-content overview-tab">
      <section className="section what-you-need-to-know">
        <h2>What You Need to Know</h2>
        <div className="key-points">
          <div className="key-point">
            <span className="kp-label">Headline</span>
            <span className="kp-value">{interpretation?.headline || '-'}</span>
          </div>
          <div className="key-point">
            <span className="kp-label">What Happened</span>
            <span className="kp-value">{interpretation?.what_happened || '-'}</span>
          </div>
          <div className="key-point">
            <span className="kp-label">What It Means</span>
            <span className="kp-value">{interpretation?.what_it_means || '-'}</span>
          </div>
          <div className="key-point">
            <span className="kp-label">Why It Matters</span>
            <span className="kp-value">{interpretation?.why_it_matters || '-'}</span>
          </div>
        </div>
      </section>

      <section className="section impact-section">
        <div className="impact-grid">
          <div className="impact-card company-impact">
            <h3>Company Impact</h3>
            <div className="impact-badge">
              <Badge variant={getImpactVariant(interpretation?.company_impact?.direction)}>
                {interpretation?.company_impact?.direction || 'unknown'}
              </Badge>
              <span className="impact-magnitude">({interpretation?.company_impact?.magnitude || 'unknown'})</span>
            </div>
            <p className="impact-horizon">Horizon: {interpretation?.company_impact?.horizon || 'unknown'}</p>
            <p className="impact-confidence">Confidence: {(interpretation?.company_impact?.confidence * 100).toFixed(0)}%</p>
            {interpretation?.company_impact?.reasons?.length > 0 && (
              <ul className="reasons-list">
                {interpretation.company_impact.reasons.map((reason: string, i: number) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="impact-card stock-impact">
            <h3>Stock Impact</h3>
            <div className="impact-badge">
              <Badge variant={getStockVariant(interpretation?.stock_impact?.bias)}>
                {interpretation?.stock_impact?.bias || 'unknown'}
              </Badge>
              <span className="impact-magnitude">({interpretation?.stock_impact?.magnitude || 'unknown'})</span>
            </div>
            <p className="impact-horizon">Horizon: {interpretation?.stock_impact?.horizon || 'unknown'}</p>
            <p className="impact-confidence">Confidence: {(interpretation?.stock_impact?.confidence * 100).toFixed(0)}%</p>
            {interpretation?.stock_impact?.reasons?.length > 0 && (
              <ul className="reasons-list">
                {interpretation.stock_impact.reasons.map((reason: string, i: number) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      <section className="section scenarios-section">
        <h2>Scenario Analysis</h2>
        <div className="scenarios-grid">
          <ScenarioCard scenario={interpretation?.base_case} variant="base" />
          <ScenarioCard scenario={interpretation?.bull_case} variant="bull" />
          <ScenarioCard scenario={interpretation?.bear_case} variant="bear" />
        </div>
      </section>

      <section className="section view-change-section">
        <h2>What Would Change the View?</h2>
        <div className="triggers-list">
          {interpretation?.what_would_change_view?.map((trigger: { trigger: string; description: string }, i: number) => (
            <div key={i} className="trigger-item">
              <strong>{trigger.trigger}</strong>
              <p>{trigger.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section confidence-section">
        <h2>Confidence Assessment</h2>
        <div className="confidence-display">
          <div className="confidence-score">{(interpretation?.confidence * 100).toFixed(0)}%</div>
          <div className="confidence-factors">
            {interpretation?.confidence_reasons?.map((r: string, i: number) => (
              <div key={i} className="confidence-factor">{r}</div>
            ))}
          </div>
          {interpretation?.missing_information?.length > 0 && (
            <div className="missing-info">
              <h4>Missing Information:</h4>
              <ul>
                {interpretation.missing_information.map((m: string, i: number) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="section evidence-section">
        <h2>Supporting Evidence</h2>
        <div className="evidence-list">
          {interpretation?.supporting_evidence?.map((ev: { source_type: string; url: string; description: string; timestamp: string }, i: number) => (
            <div key={i} className="evidence-item">
              <span className="evidence-source">{ev.source_type}</span>
              <a href={ev.url} target="_blank" rel="noopener noreferrer" className="evidence-link">
                {ev.description}
              </a>
              <span className="evidence-time">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function EarningsTab({ earnings, loading }: { earnings: EarningsEvent[] | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonCard /><SkeletonCard /></div>
  if (!earnings?.length) return <div className="empty-state">No earnings data available</div>

  return (
    <div className="tab-content earnings-tab">
      <div className="earnings-history">
        {earnings.map((e: EarningsEvent) => (
    <div key={e.event_id} className="earnings-card">
      <div className="earnings-header">
        <span className="earnings-period">{e.metadata?.fiscal_quarter} {e.metadata?.fiscal_year}</span>
        <span className="earnings-date">{format(new Date(e.released_at), 'MMM d, yyyy')}</span>
      </div>
      <div className="earnings-metrics">
        <div className="metric">
          <span className="metric-label">EPS Actual</span>
          <span className="metric-value">{e.metadata?.eps_actual || '-'}</span>
        </div>
        <div className="metric">
          <span className="metric-label">EPS Consensus</span>
          <span className="metric-value">{e.metadata?.eps_consensus || '-'}</span>
        </div>
        <div className="metric">
          <span className="metric-label">EPS Surprise</span>
          <span className={`metric-value ${e.metadata?.eps_surprise && parseFloat(e.metadata.eps_surprise) > 0 ? 'positive' : e.metadata?.eps_surprise && parseFloat(e.metadata.eps_surprise) < 0 ? 'negative' : ''}`}>
            {e.metadata?.eps_surprise ? (parseFloat(e.metadata.eps_surprise) > 0 ? '+' : '') + e.metadata.eps_surprise : '-'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Revenue</span>
          <span className="metric-value">{e.metadata?.revenue_actual ? formatNumber(e.metadata.revenue_actual) : '-'}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Rev Consensus</span>
          <span className="metric-value">{e.metadata?.revenue_consensus ? formatNumber(e.metadata.revenue_consensus) : '-'}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Rev Surprise</span>
          <span className={`metric-value ${e.metadata?.revenue_surprise && parseFloat(e.metadata.revenue_surprise) > 0 ? 'positive' : e.metadata?.revenue_surprise && parseFloat(e.metadata.revenue_surprise) < 0 ? 'negative' : ''}`}>
            {e.metadata?.revenue_surprise ? (parseFloat(e.metadata.revenue_surprise) > 0 ? '+' : '') + formatNumber(parseFloat(e.metadata.revenue_surprise)) : '-'}
          </span>
        </div>
      </div>
      {e.metadata?.guidance_change && (
        <div className="guidance-change">
          <span className="guidance-badge">{e.metadata.guidance_change}</span>
          {e.metadata?.guidance_details && (
            <div className="guidance-details">
              <span>EPS: {e.metadata.guidance_details?.eps_guidance_low} - {e.metadata.guidance_details?.eps_guidance_high}</span>
              <span>Rev: {e.metadata.guidance_details?.revenue_guidance_low} - {e.metadata.guidance_details?.revenue_guidance_high}</span>
            </div>
          )}
        </div>
      )}
    </div>
  ))}
    </div>
  </div>
)
}

function EventsTab({ events, loading }: { events: CompanyEvent[] | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><div className="skeleton-card" /><div className="skeleton-card" /></div>
  if (!events?.length) return <div className="empty-state">No events found</div>

  return (
    <div className="tab-content events-tab">
      <div className="events-list">
        {events.map((e: CompanyEvent) => (
    <div key={e.event_id} className="event-item">
      <div className="event-header">
        <span className="event-type-badge">{e.event_type}</span>
        <span className="event-time">{e.released_at ? format(new Date(e.released_at), 'MMM d, yyyy HH:mm') : 'Pending'}</span>
      </div>
      <Link to={`/stocks/${e.symbol}`} className="event-title-link">
        <h4>{e.title}</h4>
      </Link>
      <p className="event-description">{e.description?.substring(0, 300)}...</p>
      <div className="event-meta">
        <span className="event-source">{e.source}</span>
        <span className="event-importance">{e.importance}</span>
      </div>
    </div>
))}
      </div>
    </div>
  )
}

function NewsTab({ news, loading }: { news: NewsEvent[] | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonCard /><SkeletonCard /></div>
  if (!news?.length) return <div className="empty-state">No news available</div>

  return (
    <div className="tab-content news-tab">
      <div className="news-list">
        {news.map((n: NewsEvent) => (
    <article key={n.document_id} className="news-item">
      <Link to={n.source_url} target="_blank" rel="noopener noreferrer" className="news-link">
        <div className="news-header">
          <h4>{n.headline}</h4>
          <span className="news-publisher">{n.publisher}</span>
        </div>
        <p className="news-summary">{n.summary?.substring(0, 200)}...</p>
        <div className="news-meta">
          <span className="news-source">{n.source_type}</span>
          <time>{n.published_at ? format(new Date(n.published_at), 'MMM d, yyyy HH:mm') : ''}</time>
        </div>
      </Link>
    </article>
))}
      </div>
    </div>
  )
}

function InsidersTab({ insiders, loading }: { insiders: InsiderTransaction[] | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonCard /><SkeletonCard /></div>
  if (!insiders?.length) return <div className="empty-state">No insider transactions found</div>

  return (
    <div className="tab-content insiders-tab">
      <table className="insiders-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Insider</th>
            <th>Role</th>
            <th>Type</th>
            <th>Shares</th>
            <th>Price</th>
            <th>Value</th>
            <th>10b5-1</th>
            <th>Holdings After</th>
          </tr>
        </thead>
        <tbody>
          {insiders.map((i: InsiderTransaction) => {
            return (
              <tr key={i.transaction_id}>
                <td>{format(new Date(i.transaction_date), 'MMM d, yyyy')}</td>
                <td>{i.name}</td>
                <td>{i.role}</td>
                <td><Badge variant={i.transaction_type === 'purchase' ? 'success' : i.transaction_type === 'sale' ? 'error' : 'default'}>{i.transaction_type}</Badge></td>
                <td>{i.shares?.toLocaleString()}</td>
                <td>{i.price ? `$${i.price}` : '-'}</td>
                <td>{i.transaction_value ? formatNumber(i.transaction_value) : '-'}</td>
                <td>{i.is_10b5_1 ? <Badge variant="warning">10b5-1</Badge> : 'No'}</td>
                <td>{i.holdings_after?.toLocaleString() || '-'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function LeadershipTab({ leadership, loading }: { leadership: LeadershipData | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonText lines={3} /></div>
  if (!leadership || !leadership.ceo && !leadership.cfo) return <div className="empty-state">No leadership data available</div>

  return (
    <div className="tab-content leadership-tab">
      <div className="leadership-grid">
        {leadership.ceo && (
          <div className="leader-card">
            <div className="leader-avatar">CEO</div>
            <div className="leader-info">
              <h4>CEO</h4>
              <p className="leader-name">{leadership.ceo}</p>
            </div>
          </div>
        )}
        {leadership.cfo && (
          <div className="leader-card">
            <div className="leader-avatar">CFO</div>
            <div className="leader-info">
              <h4>CFO</h4>
              <p className="leader-name">{leadership.cfo}</p>
            </div>
          </div>
        )}
        {Object.entries(leadership).filter(([k, v]) => !['ceo', 'cfo'].includes(k) && v).map(([role, name]) => (
          <div key={role} className="leader-card">
            <div className="leader-avatar">{role.toUpperCase()}</div>
            <div className="leader-info">
              <h4>{role.toUpperCase()}</h4>
              <p className="leader-name">{name}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FilingsTab({ filings, loading }: { filings: Filing[] | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonCard /><SkeletonCard /></div>
  if (!filings?.length) return <div className="empty-state">No filings found</div>

  return (
    <div className="tab-content filings-tab">
      <table className="filings-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Description</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {filings.map((f: Filing) => {
            return (
              <tr key={f.event_id}>
                <td>{f.released_at ? format(new Date(f.released_at), 'MMM d, yyyy') : '-'}</td>
                <td><Badge variant="default">{f.metadata?.form || f.event_type}</Badge></td>
                <td>{f.title}</td>
                <td><a href={f.source_url || '#'} target="_blank" rel="noopener noreferrer" className="link">View</a></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function QuantTab({ quant, loading }: { quant: QuantSignals | undefined; loading: boolean }) {
  if (loading) return <div className="tab-content"><SkeletonCard /><SkeletonCard /></div>
  if (!quant) return <div className="empty-state">No quant data available</div>

  return (
    <div className="tab-content quant-tab">
      <div className="quant-signals">
        <h3>Quant Signals</h3>
        <div className="signals-grid">
          {Object.entries(quant.signals || {}).map(([key, value]: [string, number]) => (
    <div key={key} className="signal-card">
      <span className="signal-name">{key}</span>
      <span className={`signal-value ${value > 0 ? 'positive' : value < 0 ? 'negative' : ''}`}>
        {typeof value === 'number' ? value.toFixed(2) : value}
      </span>
    </div>
))}
        </div>
      </div>
    </div>
  )
}

function ScenarioCard({ scenario, variant }: { scenario: Interpretation['base_case']; variant: 'base' | 'bull' | 'bear' }) {
  const variants = {
    base: { class: 'scenario-base', label: 'BASE CASE' },
    bull: { class: 'scenario-bull', label: 'BULL CASE' },
    bear: { class: 'scenario-bear', label: 'BEAR CASE' },
  }

  const v = variants[variant]

  return (
    <div className={`scenario-card ${v.class}`}>
      <div className="scenario-header">
        <span className="scenario-label">{v.label}</span>
        {scenario.probability_band && <span className="probability">{scenario.probability_band}</span>}
      </div>
      <p className="scenario-description">{scenario.description}</p>
      {scenario.required_conditions?.length > 0 && (
        <div className="scenario-conditions">
          <strong>Required conditions:</strong>
          <ul>
            {scenario.required_conditions.map((c: string, i: number) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function getImpactVariant(direction: string) {
  switch (direction) {
    case 'positive': return 'success'
    case 'negative': return 'error'
    case 'mixed': return 'warning'
    default: return 'default'
  }
}

function getStockVariant(bias: string) {
  switch (bias) {
    case 'bullish': return 'success'
    case 'bearish': return 'error'
    case 'mixed': return 'warning'
    default: return 'default'
  }
}

function formatNumber(num: number): string {
  if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toLocaleString()
}

export default StockPage