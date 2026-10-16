import { useState, type RefObject } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'

export function Header({ navigationExpanded, onToggleNavigation, toggleRef }: { navigationExpanded: boolean; onToggleNavigation: () => void; toggleRef: RefObject<HTMLButtonElement> }) {
  const { pathname, search } = useLocation()
  const routeKey = pathname + search
  const routeQuery = pathname === '/search' ? new URLSearchParams(search).get('q') : null
  const [field, setField] = useState(() => ({ routeKey, query: routeQuery ?? '' }))
  const navigate = useNavigate()
  // Adjust only on URL changes; theme/layout renders must preserve a draft.
  if (field.routeKey !== routeKey) setField({ routeKey, query: routeQuery ?? field.query })
  const query = field.query

  return (
    <header className="header" role="banner">
      <div className="header-container">
        <button ref={toggleRef} type="button" className="shell-nav-toggle" onClick={onToggleNavigation} aria-controls="primary-sidebar" aria-expanded={navigationExpanded} aria-label={navigationExpanded ? 'Collapse navigation' : 'Expand navigation'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <Link to="/" className="header-logo" aria-label="Trading Copilot Home">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="currentColor" />
            <path d="M8 12h16M8 16h12M8 20h8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="logo-text">Trading Copilot</span>
        </Link>

        <form className="shell-search" role="search" aria-label="Global stock search" onSubmit={event => { event.preventDefault(); if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`) }}>
          <label className="sr-only" htmlFor="global-stock-search">Search stocks or companies</label>
          <input id="global-stock-search" type="search" placeholder="Search stocks or companies" value={query} onChange={event => setField({ routeKey, query: event.target.value })} />
          <button type="submit" aria-label="Submit stock search" disabled={!query.trim()}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="10" cy="10" r="7" /><path d="m15 15 6 6" /></svg></button>
        </form>

        <div className="header-actions">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="theme-toggle" role="group" aria-label="Theme selection">
      <button
        type="button"
        className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
        onClick={() => setTheme('light')}
        aria-pressed={theme === 'light'}
        aria-label="Light theme"
        title="Light theme"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      </button>
      <button
        type="button"
        className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
        onClick={() => setTheme('dark')}
        aria-pressed={theme === 'dark'}
        aria-label="Dark theme"
        title="Dark theme"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </button>
      <button
        type="button"
        className={`theme-btn ${theme === 'system' ? 'active' : ''}`}
        onClick={() => setTheme('system')}
        aria-pressed={theme === 'system'}
        aria-label="System theme"
        title="System theme"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      </button>
    </div>
  )
}
