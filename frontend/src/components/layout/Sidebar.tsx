import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const navigation = [
  { label: 'Dashboard', href: '/', icon: 'dashboard' },
  { label: 'Scanner', href: '/scanner', icon: 'scanner' },
  { label: 'Macro Calendar', href: '/macro', icon: 'calendar' },
  { label: 'Watchlists', href: '/watchlists', icon: 'watchlist' },
  { label: 'Calendar', href: '/calendar', icon: 'calendar-export' },
  { label: 'Alerts', href: '/alerts', icon: 'alert' },
  { label: 'Search', href: '/search', icon: 'search' },
  { label: 'Settings', href: '/settings', icon: 'settings' },
]

export function Sidebar({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const location = useLocation()

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`} aria-label="Sidebar navigation">

      <nav className="sidebar-nav" aria-label="Main navigation">
        <ul className="nav-list" role="list">
          {navigation.map((item) => (
            <li key={item.href}>
              <Link
                to={item.href}
                onClick={onNavigate}
                title={collapsed ? item.label : undefined}
                className={`nav-item ${location.pathname === item.href || location.pathname.startsWith(`${item.href}/`) ? 'active' : ''}`}
                aria-current={location.pathname === item.href || location.pathname.startsWith(`${item.href}/`) ? 'page' : undefined}
                aria-label={collapsed ? item.label : undefined}
              >
                <span className="nav-icon" aria-hidden="true">
                  {getIcon(item.icon)}
                </span>
                {!collapsed && <span className="nav-label">{item.label}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

    </aside>
  )
}

function getIcon(name: string) {
  const icons: Record<string, React.ReactNode> = {
    dashboard: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
    scanner: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2m-2 2H5a2 2 0 0 1-2-2v-2m0 0L7 7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 7v10" strokeWidth="2" strokeLinecap="round" />
        <path d="M15 7v10" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    calendar: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
        <path d="M8 14h.01M12 14h.01M16 14h.01" />
      </svg>
    ),
    watchlist: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" />
        <path d="M9 3v18" />
        <path d="M15 3v18" />
        <path d="M9 9h6" />
        <path d="M9 15h6" />
      </svg>
    ),
    'calendar-export': (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
        <path d="M8 14h.01M12 14h.01M16 14h.01" />
        <path d="M12 16v-4l-2 2" />
      </svg>
    ),
    alert: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
    search: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
    settings: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82.33 1.65 1.65 0 0 1-1.82-.33l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 1 1.82-.33H21a6 6 0 0 0 0-12h-6a6 6 0 0 0-6 5.66 6 6 0 0 1-6 5.66" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  }
  return icons[name] || null
}
