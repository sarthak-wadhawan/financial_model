import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { useDebounce } from '../hooks/useDebounce'
import { DataStatus } from '../components/ui/ResearchData'

export function SearchPage() {
  const [query, setQuery] = useState('')
  const search = useDebounce(query.trim(), 300)
  const results = useQuery({ queryKey: ['search', search], queryFn: () => api.searchSymbols(search), enabled: search.length >= 1, staleTime: 60000 })
  return <div className="page search-page">
    <div className="page-header"><h1>Search Stocks</h1><p className="page-subtitle">Find a company by symbol or name, then explore its evidence and interpretation.</p></div>
    <form className="search-form" onSubmit={e => e.preventDefault()}>
      <label htmlFor="stock-search">Symbol or company name</label>
      <div className="search-input-wrapper"><input id="stock-search" type="search" className="search-input" placeholder="e.g. AAPL" value={query} onChange={e => setQuery(e.target.value)} /><button className="search-submit" type="submit">Search</button></div>
    </form>
    {!search ? <p className="search-hints">Enter a symbol or company name. Coverage depends on the connected provider.</p> : <section className="results-section" aria-label="Stock search results">
      <DataStatus loading={results.isLoading || query.trim() !== search} error={results.isError} empty={results.isSuccess && !results.data?.length} label="matching stocks" />
      {results.isSuccess && query.trim() === search && <><div className="results-header"><h2>Stocks</h2><span className="results-count">{results.data.length} results</span></div><div className="results-grid">{results.data.map(stock => <Link key={stock.symbol} to={`/stocks/${encodeURIComponent(stock.symbol)}`} className="result-card stock-card"><div className="result-header"><strong className="result-symbol">{stock.symbol}</strong><span className="result-exchange">{stock.exchange ?? 'Exchange unavailable'}</span></div><div className="result-name">{stock.name ?? 'Company name unavailable'}</div><span className="result-asset-type">{stock.type} · Source: {stock.source}</span></Link>)}</div></>}
      {results.isError && <button className="btn btn-secondary" onClick={() => results.refetch()}>Retry search</button>}
    </section>}
  </div>
}
export default SearchPage
