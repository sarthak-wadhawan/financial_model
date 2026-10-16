import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { DataStatus, displayDate, displayNumber, Term } from '../components/ui/ResearchData'

export function ScannerPage() {
  const [topN, setTopN] = useState(20)
  const [filter, setFilter] = useState('')
  const scanner = useQuery({ queryKey: ['scannerTop', topN], queryFn: () => api.getQuantScannerTop(topN), staleTime: 300000 })
  const market = useQuery({ queryKey: ['marketOverview'], queryFn: () => api.getMarketOverview(), staleTime: 300000 })
  // Read status only after this scan completes. Key by completion so a late
  // response from an older scan cannot overwrite the current provenance.
  const status = useQuery({ queryKey: ['scannerStatus', topN, scanner.dataUpdatedAt], queryFn: () => api.getScannerStatus(), enabled: scanner.isSuccess && !scanner.isFetching, staleTime: 0 })
  const candidates = scanner.data?.filter(candidate => candidate.symbol.includes(filter.trim().toUpperCase()))
  return <div className="page scanner-page">
    <div className="page-header"><div className="page-header-content"><h1>Quant Scanner</h1><p className="page-subtitle">Deterministic rankings for research. Scores are not price forecasts or trade recommendations.</p></div></div>
    <div className="scanner-toolbar"><div className="page-header-actions"><label htmlFor="scanner-count">Results</label><select id="scanner-count" className="select-input" value={topN} onChange={e => setTopN(Number(e.target.value))}>{[10,20,50,100].map(n => <option key={n} value={n}>Top {n}</option>)}</select><label htmlFor="scanner-filter">Filter returned symbols</label><input id="scanner-filter" className="search-input" value={filter} onChange={e => setFilter(e.target.value)} placeholder="e.g. AAPL" /><button className="btn btn-secondary" disabled={scanner.isFetching} onClick={() => scanner.refetch()}>{scanner.isFetching ? 'Refreshing…' : 'Refresh results'}</button></div></div>
    <div className="scanner-stats"><div className="stat"><span className="stat-label">Market status</span><span className="stat-value">{market.data?.market_status ?? 'Unavailable'}</span></div><div className="stat"><span className="stat-label">Symbols tracked</span><span className="stat-value">{market.data?.symbols_tracked ?? 'Unavailable'}</span></div><div className="stat"><span className="stat-label">Calculation date</span><span className="stat-value">{displayDate(status.data?.calculated_at)}</span></div></div>
    <DataStatus loading={status.isLoading} error={status.isError} label="scanner provenance" />
    {status.data && !scanner.isFetching && <p className="data-status">Mode: {status.data.mode} · Status: {status.data.status} · Source: {status.data.source} · Market date: {displayDate(status.data.market_timestamp)}{status.data.reason ? ` · ${status.data.reason}` : ''}</p>}
    <DataStatus error={market.isError} label="market status" />
    <DataStatus loading={scanner.isLoading} error={scanner.isError} empty={scanner.isSuccess && !scanner.data?.length} label="scanner candidates from the connected provider" />
    {scanner.data && !scanner.isError && <><p className="data-status">{candidates?.length} of {scanner.data.length} returned candidates. Filtering preserves backend ranks and scores.</p>{!candidates?.length && !!scanner.data.length ? <p className="empty-state">No returned symbols match this filter.</p> : !!candidates?.length && <div className="scanner-table-container" tabIndex={0} role="region" aria-label="Scanner results, scroll horizontally for all scores"><table className="scanner-table"><caption>Backend rankings and component scores</caption><thead><tr><th scope="col">Rank</th><th scope="col">Symbol</th><th scope="col">Quant Score</th><th scope="col"><Term term="momentum">Momentum</Term></th><th scope="col">Trend</th><th scope="col"><Term term="liquidity">Liquidity</Term></th><th scope="col">Volume</th><th scope="col">Vol Quality</th><th scope="col">Price</th></tr></thead><tbody>{candidates.map(candidate => <tr key={candidate.symbol}><td className="rank">#{candidate.rank}</td><td><Link className="symbol-link" to={`/stocks/${candidate.symbol}`}>{candidate.symbol}</Link></td>{[candidate.quant_score, candidate.momentum_score, candidate.trend_score, candidate.liquidity_score, candidate.volume_score, candidate.volatility_quality_score].map((score, i) => <td key={i} className="score-cell">{displayNumber(score)}</td>)}<td className="price-cell">{typeof candidate.price === 'number' ? `$${displayNumber(candidate.price, 2)}` : 'Unavailable'}</td></tr>)}</tbody></table></div>}</>}
  </div>
}
export default ScannerPage
