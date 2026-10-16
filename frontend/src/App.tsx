import { Suspense, lazy, useRef, useState } from 'react'
import { Routes, Route, Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from './services/api'
import { useMediaQuery } from './hooks'
import { DataStatus } from './components/ui/ResearchData'
import { Header } from './components/layout/Header'
import { Sidebar } from './components/layout/Sidebar'
import { Footer } from './components/layout/Footer'
import { LoadingSpinner } from './components/ui/LoadingSpinner'
import { Toaster } from './components/ui/Toaster'
import { useTheme } from './context/ThemeContext'

// Lazy load pages
const LandingPage = lazy(() => import('./pages/LandingPage'))
const StockPage = lazy(() => import('./pages/StockPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const MacroCalendarPage = lazy(() => import('./pages/MacroCalendarPage'))
const ScannerPage = lazy(() => import('./pages/ScannerPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const AlertsPage = lazy(() => import('./pages/AlertsPage'))

function App() {
  const { resolvedTheme } = useTheme()
  const mobile = useMediaQuery('(max-width: 768px)')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const toggleRef = useRef<HTMLButtonElement>(null)
  const closeMobileNavigation = () => { setMobileOpen(false); toggleRef.current?.focus() }

  return (
    <div className={`app ${resolvedTheme}`}>
        <div className={`app-layout shell-layout ${collapsed ? 'navigation-collapsed' : ''}`} onKeyDown={event => { if (event.key === 'Escape' && mobile && mobileOpen) { event.preventDefault(); closeMobileNavigation() } }}>
          <a className="skip-link" href="#main-content">Skip to content</a>
          <div className="app-header">
            <Header navigationExpanded={mobile ? mobileOpen : !collapsed} onToggleNavigation={() => mobile ? setMobileOpen(!mobileOpen) : setCollapsed(!collapsed)} toggleRef={toggleRef} />
          </div>
          
          <div className="app-main">
            <div className="app-sidebar" id="primary-sidebar" hidden={mobile && !mobileOpen}>
              <Sidebar collapsed={!mobile && collapsed} onNavigate={() => { if (mobile) closeMobileNavigation() }} />
            </div>
            
            <main className="app-content" id="main-content" tabIndex={-1}>
              <Suspense fallback={<LoadingSpinner size="lg" />}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/stocks/:symbol" element={<StockPage />} />
                <Route path="/search" element={<SearchRoute />} />
                <Route path="/macro" element={<MacroCalendarPage />} />
                <Route path="/scanner" element={<ScannerPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/watchlists" element={<WatchlistPage />} />
                <Route path="/watchlists/:watchlistId" element={<WatchlistPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
              </Suspense>
            </main>
          </div>
          
          <div className="app-footer">
            <Footer />
          </div>
        </div>
      <Toaster />
    </div>
  )
}

export default App

// Preserve the existing free-form search page, while making URL searches shareable.
function SearchRoute() {
  const [params] = useSearchParams()
  const query = params.get('q')?.trim() ?? ''
  const results = useQuery({ queryKey: ['search', query], queryFn: () => api.searchSymbols(query), enabled: !!query, staleTime: 60000 })
  if (!query) return <SearchPage />
  return <div className="page search-page">
    <div className="page-header"><h1>Search Stocks</h1><p className="page-subtitle">Results for “{query}”</p></div>
    <DataStatus loading={results.isLoading} error={results.isError} empty={results.isSuccess && !results.data?.length} label="matching stocks" />
    {results.isSuccess && <div className="results-grid">{results.data.map(stock => <Link key={stock.symbol} to={`/stocks/${encodeURIComponent(stock.symbol)}`} className="result-card"><strong>{stock.symbol}</strong><p className="result-name">{stock.name ?? 'Company name unavailable'}</p><span className="result-meta">{stock.exchange ?? 'Exchange unavailable'} · Source: {stock.source}</span></Link>)}</div>}
    {results.isError && <button className="btn btn-secondary" onClick={() => results.refetch()}>Retry search</button>}
    <Link className="btn btn-link" to="/search">New search</Link>
  </div>
}
