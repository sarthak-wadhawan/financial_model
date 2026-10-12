import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

interface SymbolSearchResult {
  symbol: string
  name: string
  exchange: string
  type: string
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => api.searchSymbols(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 1000 * 60,
  })

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim().length >= 2) {
      setDebouncedQuery(query)
    }
  }

  if (!query.trim()) {
    return (
      <div className="page search-page">
        <div className="search-hero">
          <h1>Search</h1>
          <p className="search-subtitle">Find stocks, news, events, and filings</p>
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-input-wrapper">
              <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search stocks, news, events, filings..."
                className="search-input"
                autoFocus
              />
              <button type="submit" className="search-submit" aria-label="Search">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            </div>
          </form>
          <div className="search-hints">
            <span>Try: "AAPL", "earnings", "FOMC", "Form 4"</span>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="page search-page">
        <div className="search-hero">
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-input-wrapper">
              <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search stocks, news, events, filings..."
                className="search-input"
                autoFocus
              />
              <button type="submit" className="search-submit" aria-label="Search">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            </div>
          </form>
        </div>
        <div className="search-loading">
          <div className="loading-spinner-container">
            <LoadingSpinner size="lg" />
            <p>Searching...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page search-page">
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search stocks, news, events, filings..."
            className="search-input"
            autoFocus
          />
          <button type="submit" className="search-submit" aria-label="Search">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </button>
        </div>
      </form>

      {isLoading ? (
        <div className="search-results-loading">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="search-results">
          <section className="results-section">
            <div className="results-header">
              <h3>Stocks</h3>
              <span className="results-count">{results?.length || 0} results</span>
            </div>
            <div className="results-grid">
              {results?.map((stock: SymbolSearchResult) => (
                <Link key={stock.symbol} to={`/stocks/${stock.symbol}`} className="result-card stock-card">
                  <div className="result-header">
                    <span className="result-symbol">{stock.symbol}</span>
                    <span className="result-exchange">{stock.exchange}</span>
                  </div>
                  <div className="result-name">{stock.name}</div>
                  <div className="result-meta">
                    <span className="result-asset-type">{stock.type}</span>
                  </div>
                </Link>
              ))}
              {(!results || results.length === 0) && (
                <div className="empty-state">No stocks found matching "{query}"</div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default SearchPage