import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { api } from '../../services/api'
import { LoadingSpinner, SkeletonCard, SkeletonText } from '../ui/LoadingSpinner'
import { Badge, Tabs, Tab } from '../ui'

interface SearchResult {
  symbol: string
  name: string
  exchange: string
  asset_type: string
}

interface SearchResults {
  stocks: SearchResult[]
  news: any[]
  events: any[]
  filings: any[]
  total: number
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [activeTab, setActiveTab] = useState('all')

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

  const tabs = [
    { id: 'all', label: 'All' },
    { id: 'stocks', label: 'Stocks' },
    { id: 'news', label: 'News' },
    { id: 'events', label: 'Events' },
    { id: 'filings', label: 'Filings' },
  ]

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
                placeholder="Search stocks, news, events, filings..."
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

      <div className="search-tabs">
        <Tabs
          tabs={[
            { id: 'all', label: 'All' },
            { id: 'stocks', label: 'Stocks' },
            { id: 'news', label: 'News' },
            { id: 'events', label: 'Events' },
            { id: 'filings', label: 'Filings' },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {isLoading && activeTab === 'all' ? (
        <div className="search-results-loading">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="search-results">
          {activeTab === 'all' || activeTab === 'stocks' ? (
            <section className="results-section">
              <div className="results-header">
                <h3>Stocks</h3>
                <span className="results-count">{results?.stocks?.length || 0} results</span>
              </div>
              <div className="results-grid">
                {results?.stocks?.map((stock: any) => (
                  <Link key={stock.symbol} to={`/stocks/${stock.symbol}`} className="result-card stock-card">
                    <div className="result-header">
                      <span className="result-symbol">{stock.symbol}</span>
                      <span className="result-exchange">{stock.exchange}</span>
                    </div>
                    <div className="result-name">{stock.name}</div>
                    <div className="result-meta">
                      <span className="result-asset-type">{stock.asset_type}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          {activeTab === 'all' || activeTab === 'news' ? (
            <section className="results-section">
              <div className="results-header">
                <h3>News</h3>
                <span className="results-count">{results?.news?.length || 0} results</span>
              </div>
              <div className="results-list">
                {results?.news?.map((item: any) => (
                  <Link key={item.document_id} to={item.source_url} target="_blank" rel="noopener noreferrer" className="result-card news-card">
                    <div className="news-header">
                      <span className="news-publisher">{item.publisher}</span>
                      <time>{item.published_at ? format(new Date(item.published_at), 'MMM d, yyyy HH:mm') : ''}</time>
                    </div>
                    <h4>{item.headline}</h4>
                    <p className="news-summary">{item.summary?.substring(0, 200)}...</p>
                    <div className="news-meta">
                      <span className="news-source">{item.source_type}</span>
                      {item.symbol && <Badge variant="secondary">{item.symbol}</Badge>}
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          {activeTab === 'all' || activeTab === 'events' ? (
            <section className="results-section">
              <div className="results-header">
                <h3>Events</h3>
                <span className="results-count">{results?.events?.length || 0} results</span>
              </div>
              <div className="results-list">
                {results?.events?.map((item: any) => (
                  <Link key={item.event_id} to={`/stocks/${item.symbol}`} className="result-card event-card">
                    <div className="event-header">
                      <span className="event-type-badge">{item.event_type}</span>
                      <span className="event-date">{item.released_at ? format(new Date(item.released_at), 'MMM d, yyyy HH:mm') : 'Pending'}</span>
                    </div>
                    <h4>{item.title}</h4>
                    <div className="event-meta">
                      <span className="event-symbol">{item.symbol}</span>
                      <span className="event-importance">{item.importance}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          {activeTab === 'all' || activeTab === 'filings' ? (
            <section className="results-section">
              <div className="results-header">
                <h3>Filings</h3>
                <span className="results-count">{results?.filings?.length || 0} results</span>
              </div>
              <div className="results-list">
                {results?.filings?.map((item: any) => (
                  <Link key={item.event_id} to={`/stocks/${item.symbol}`} className="result-card filing-card">
                    <div className="filing-header">
                      <span className="filing-type">{item.metadata?.form || item.event_type}</span>
                      <time>{item.released_at ? format(new Date(item.released_at), 'MMM d, yyyy') : ''}</time>
                    </div>
                    <h4>{item.title}</h4>
                    <div className="filing-meta">
                      <span className="filing-symbol">{item.symbol}</span>
                      <span className="filing-source">{item.source}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </div>
  )
}

export default SearchPage