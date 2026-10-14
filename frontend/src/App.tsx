import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
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

  return (
    <div className={`app ${resolvedTheme}`}>
      <Suspense fallback={<LoadingSpinner size="lg" />}>
        <div className="app-layout">
          <a className="skip-link" href="#main-content">Skip to content</a>
          <div className="app-header">
            <Header />
          </div>
          
          <div className="app-main">
            <div className="app-sidebar">
              <Sidebar />
            </div>
            
            <main className="app-content" id="main-content" tabIndex={-1}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/stocks/:symbol" element={<StockPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/macro" element={<MacroCalendarPage />} />
                <Route path="/scanner" element={<ScannerPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/watchlists" element={<WatchlistPage />} />
                <Route path="/watchlists/:watchlistId" element={<WatchlistPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/alerts" element={<AlertsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </main>
          </div>
          
          <div className="app-footer">
            <Footer />
          </div>
        </div>
      </Suspense>
      <Toaster />
    </div>
  )
}

export default App
