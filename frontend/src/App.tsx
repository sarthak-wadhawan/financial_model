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

function App() {
  const { resolvedTheme } = useTheme()

  return (
    <div className={`app ${resolvedTheme}`}>
      <Suspense fallback={<LoadingSpinner size="lg" />}>
        <div className="app-layout">
          <header className="app-header">
            <Header />
          </header>
          
          <main className="app-main">
            <aside className="app-sidebar">
              <Sidebar />
            </aside>
            
            <main className="app-content">
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/stocks/:symbol" element={<StockPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/macro" element={<MacroCalendarPage />} />
                <Route path="/scanner" element={<ScannerPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </main>
          </main>
          
          <footer className="app-footer">
            <Footer />
          </footer>
        </div>
      </Suspense>
      <Toaster />
    </div>
  )
}

export default App