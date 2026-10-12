import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { api } from '../../services/api'
import { LoadingSpinner, SkeletonCard } from '../ui/LoadingSpinner'
import { Badge, Tabs, Tab } from '../ui'

interface QuantCandidate {
  symbol: string
  quant_score: number
  momentum_score: number
  trend_score: number
  liquidity_score: number
  volume_score: number
  volatility_quality_score: number
  price: number
  as_of: string
}

export function ScannerPage() {
  const [topN, setTopN] = useState(20)

  const { data: candidates, isLoading } = useQuery({
    queryKey: ['scannerTop', topN],
    queryFn: () => api.getQuantScannerTop(topN),
    staleTime: 1000 * 60 * 5,
  })

  const { data: marketOverview } = useQuery({
    queryKey: ['marketOverview'],
    queryFn: () => api.getMarketOverview(),
    staleTime: 1000 * 60 * 5,
  })

  if (isLoading) {
    return (
      <div className="page scanner-page">
        <div className="page-header">
          <h1>Quant Scanner</h1>
          <p className="page-subtitle">Top ranked stocks by deterministic quant signals</p>
        </div>
        <div className="scanner-loading">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  return (
    <div className="page scanner-page">
      <div className="page-header">
        <div className="page-header-content">
          <h1>Quant Scanner</h1>
          <p className="page-subtitle">Top ranked stocks by deterministic quant signals</p>
        </div>
        <div className="page-header-actions">
          <select
            value={topN}
            onChange={e => setTopN(Number(e.target.value))}
            className="select-input"
            aria-label="Number of results"
          >
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={50}>Top 50</option>
            <option value={100}>Top 100</option>
          </select>
        </div>
      </div>

      <div className="scanner-toolbar">
        <div className="scanner-stats">
          <div className="stat">
            <span className="stat-label">Universe</span>
            <span className="stat-value">{marketOverview?.universe_size || 0}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Eligible</span>
            <span className="stat-value">{marketOverview?.eligible_count || 0}</span>
          </div>
          <div className="stat">
            <span className="stat-label">As of</span>
            <span className="stat-value">{marketOverview?.as_of ? format(new Date(marketOverview.as_of), 'MMM d, yyyy') : '—'}</span>
          </div>
        </div>
      </div>

      {candidates && candidates.length > 0 ? (
        <div className="scanner-table-container">
          <table className="scanner-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Symbol</th>
                <th>Quant Score</th>
                <th>Momentum</th>
                <th>Trend</th>
                <th>Liquidity</th>
                <th>Volume</th>
                <th>Vol Quality</th>
                <th>Price</th>
                <th>As Of</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate: any, index: number) => (
                <tr key={candidate.symbol}>
                  <td className="rank">#{index + 1}</td>
                  <td>
                    <Link to={`/stocks/${candidate.symbol}`} className="symbol-link">
                      {candidate.symbol}
                    </Link>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.quant_score >= 70 ? 'high' : candidate.quant_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.quant_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.momentum_score >= 70 ? 'high' : candidate.momentum_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.momentum_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.trend_score >= 70 ? 'high' : candidate.trend_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.trend_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.liquidity_score >= 70 ? 'high' : candidate.liquidity_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.liquidity_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.volume_score >= 70 ? 'high' : candidate.volume_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.volume_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className={`score ${candidate.volatility_quality_score >= 70 ? 'high' : candidate.volatility_quality_score >= 50 ? 'medium' : 'low'}`}>
                      {candidate.volatility_quality_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="price-cell">${candidate.price?.toFixed(2) || '—'}</td>
                  <td className="date-cell">{candidate.as_of ? format(new Date(candidate.as_of), 'MMM d, yyyy') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h3>No candidates found</h3>
          <p>Try adjusting your scanner parameters or check back later.</p>
        </div>
      )}
    </div>
  )
}

export default ScannerPage