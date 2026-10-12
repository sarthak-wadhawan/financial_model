import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

export function LandingPage() {
  const { data: macroEvents } = useQuery({
    queryKey: ['macroEvents', 'upcoming'],
    queryFn: () => fetch('/api/v1/events/upcoming?days=30&limit=10').then(r => r.json()),
    staleTime: 1000 * 60 * 5,
  })

  const { data: topCandidates } = useQuery({
    queryKey: ['topCandidates'],
    queryFn: () => fetch('/api/v1/scanner/top?n=5').then(r => r.json()),
    staleTime: 1000 * 60 * 5,
  })

  const { data: recentEvents } = useQuery({
    queryKey: ['recentEvents', 7],
    queryFn: () => fetch('/api/v1/events/recent?days=7&limit=10').then(r => r.json()),
    staleTime: 1000 * 60 * 5,
  })

  return (
    <div className="landing-page">
      <section className="hero">
        <div className="hero-content">
          <h1>Trading Copilot</h1>
          <p className="hero-subtitle">
            Deterministic financial intelligence. Evidence-first research for individual investors.
          </p>
          <div className="hero-actions">
            <Link to="/scanner" className="btn btn-primary btn-lg">
              Launch Scanner
            </Link>
            <Link to="/search" className="btn btn-secondary btn-lg">
              Search Stocks
            </Link>
          </div>
        </div>
      </section>

      <section className="section market-overview">
        <div className="section-header">
          <h2>Market Overview</h2>
          <Link to="/macro" className="link">View all macro events →</Link>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">S&P 500 (SPY)</span>
            <span className="metric-value">—</span>
            <span className="metric-change neutral">—</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">VIX</span>
            <span className="metric-value">—</span>
            <span className="metric-change neutral">—</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">DXY</span>
            <span className="metric-value">—</span>
            <span className="metric-change neutral">—</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">10Y Yield</span>
            <span className="metric-value">—</span>
            <span className="metric-change neutral">—</span>
          </div>
        </div>
      </section>

      <section className="section upcoming-macro">
        <div className="section-header">
          <h2>Upcoming Macro Events</h2>
          <Link to="/macro" className="link">View all →</Link>
        </div>
        <div className="events-list">
          {macroEvents?.slice(0, 5).map((event: any) => (
            <div key={event.event_id} className="event-item">
              <div className="event-date">
                <span className="event-day">{event.scheduled_at ? new Date(event.scheduled_at).getDate() : '—'}</span>
                <span className="event-month">{event.scheduled_at ? new Date(event.scheduled_at).toLocaleString('default', { month: 'short' }) : '—'}</span>
              </div>
              <div className="event-info">
                <span className="event-title">{event.title}</span>
                <span className="event-source">{event.source}</span>
              </div>
              <div className="event-importance">
                <span className={`importance-badge ${event.importance?.toLowerCase()}`}>
                  {event.importance}
                </span>
              </div>
            </div>
          ))}
          {(!macroEvents || macroEvents.length === 0) && (
            <div className="empty-state">No upcoming macro events</div>
          )}
        </div>
      </section>

      <section className="section top-candidates">
        <div className="section-header">
          <h2>Top Scanner Candidates</h2>
          <Link to="/scanner" className="link">View scanner →</Link>
        </div>
        <div className="candidates-table-container">
          <table className="candidates-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Symbol</th>
                <th>Score</th>
                <th>Momentum</th>
                <th>Trend</th>
                <th>Liquidity</th>
                <th>Volume</th>
                <th>Vol Quality</th>
              </tr>
            </thead>
            <tbody>
              {topCandidates?.map((candidate: any) => (
                <tr key={candidate.symbol}>
                  <td className="rank">#{candidate.rank || '—'}</td>
                  <td><Link to={`/stocks/${candidate.symbol}`} className="symbol-link">{candidate.symbol}</Link></td>
                  <td className="score">{candidate.quant_score?.toFixed(1) || '—'}</td>
                  <td>{candidate.momentum_score?.toFixed(1) || '—'}</td>
                  <td>{candidate.trend_score?.toFixed(1) || '—'}</td>
                  <td>{candidate.liquidity_score?.toFixed(1) || '—'}</td>
                  <td>{candidate.volume_score?.toFixed(1) || '—'}</td>
                  <td>{candidate.volatility_quality_score?.toFixed(1) || '—'}</td>
                </tr>
              ))}
              {(!topCandidates || topCandidates.length === 0) && (
                <tr><td colSpan={8} className="empty-state">No candidates available</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section recent-events">
        <div className="section-header">
          <h2>Recent Company Events</h2>
          <Link to="/search" className="link">View all →</Link>
        </div>
        <div className="events-list">
          {recentEvents?.map((event: any) => (
            <div key={event.event_id} className="event-item">
              <div className="event-meta">
                <span className="event-symbol">{event.symbol}</span>
                <span className="event-time">{event.released_at ? format(new Date(event.released_at), 'MMM d, HH:mm') : 'Pending'}</span>
              </div>
              <Link to={`/stocks/${event.symbol}`} className="event-title">
                {event.title}
              </Link>
              <span className={`importance-badge ${event.importance?.toLowerCase()}`}>
                {event.importance}
              </span>
            </div>
          ))}
          {(!recentEvents || recentEvents.length === 0) && (
            <div className="empty-state">No recent events</div>
          )}
        </div>
      </section>

      <section className="section features">
        <h2>Why Trading Copilot?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Deterministic Intelligence</h3>
            <p>No hallucinations. Every claim traced to primary sources with evidence.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h3>Evidence-First</h3>
            <p>Every claim traced to SEC filings, earnings calls, macro data with citations.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚖️</div>
            <h3>Company ≠ Stock Impact</h3>
            <p>Fundamental business impact separated from stock price bias with confidence.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Scenario Analysis</h3>
            <p>Base/Bull/Bear cases with explicit conditions and falsification criteria.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📚</div>
            <h3>Term Definitions</h3>
            <p>Hover any financial term for instant definition with authoritative source.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>Zero-LLM Core</h3>
            <p>All core functionality works without LLMs. Optional local AI only enhances.</p>
          </div>
        </div>
      </section>

      <section className="section cta">
        <h2>Start Your Research</h2>
        <p>Evidence-first stock research. No hallucinations. No hidden agendas.</p>
        <Link to="/scanner" className="btn btn-primary btn-lg">
          Start Researching
        </Link>
      </section>
    </div>
  )
}

export default LandingPage