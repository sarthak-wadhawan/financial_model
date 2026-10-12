import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { api } from '../../services/api'
import { LoadingSpinner, SkeletonCard, SkeletonText } from '../ui/LoadingSpinner'
import { Badge, Tabs } from '../ui'

interface MacroEvent {
  event_id: string
  title: string
  event_type: string
  scheduled_at: string | null
  released_at: string | null
  actual: string | null
  forecast: string | null
  previous: string | null
  importance: string
  status: string
  source: string
  source_url: string | null
}

export function MacroCalendarPage() {
  const { data: events, isLoading } = useQuery({
    queryKey: ['macroEvents', 'all'],
    queryFn: () => fetch('/api/v1/events/macro?limit=100').then(r => r.json()),
    staleTime: 1000 * 60 * 5,
  })

  const { data: upcoming } = useQuery({
    queryKey: ['upcomingEvents', 30],
    queryFn: () => fetch('/api/v1/events/upcoming?days=30&limit=50').then(r => r.json()),
    staleTime: 1000 * 60 * 5,
  })

  const [filterImportance, setFilterImportance] = useState<string>('all')
  const [filterType, setFilterType] = useState<string>('all')
  const [activeTab, setActiveTab] = useState<string>('upcoming')

  const filteredEvents = useMemo(() => {
    return events?.filter(e => {
      if (filterImportance !== 'all' && e.importance !== filterImportance) return false
      if (filterType !== 'all' && e.event_type !== filterType) return false
      return true
    }) || []
  }, [events, filterImportance, filterType])

  const getFilteredEvents = useMemo(() => {
    const base = filteredEvents
    switch (activeTab) {
      case 'upcoming':
        return base.filter(e => e.status === 'SCHEDULED' || e.status === 'UPDATED')
      case 'recent':
        return base.filter(e => e.status === 'RELEASED')
      default:
        return base
    }
  }, [filteredEvents, activeTab])

  const importanceLevels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
  const eventTypes = ['FOMC', 'CPI', 'NFP', 'PCE', 'GDP', 'PPI', 'UNEMPLOYMENT', 'RETAIL_SALES', 'HOUSING_STARTS', 'BUILDING_PERMITS', 'JOLTS', 'FOMC_MINUTES']

  if (isLoading) return <div className="page-loading"><LoadingSpinner size="lg" /></div>

  return (
    <div className="page macro-calendar-page">
      <div className="page-header">
        <h1>Macro Calendar</h1>
        <p className="page-subtitle">Track market-moving economic events and central bank decisions</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label htmlFor="importance-filter">Importance</label>
          <select
            value={filterImportance}
            onChange={e => setFilterImportance(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Importance</option>
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="type-filter">Event Type</label>
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Types</option>
            {eventTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>

        <div className="filter-actions">
          <button className="btn btn-secondary btn-sm" onClick={() => { setFilterImportance('all'); setFilterType('all') }}>
            Clear Filters
          </button>
        </div>
      </div>

      <div className="calendar-view">
        <div className="calendar-tabs">
          <Tabs
            tabs={[
              { id: 'upcoming', label: 'Upcoming' },
              { id: 'recent', label: 'Recent' },
              { id: 'all', label: 'All Events' },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />
        </div>

        <div className="events-table-container">
          <table className="events-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Event</th>
                <th>Type</th>
                <th>Actual</th>
                <th>Forecast</th>
                <th>Previous</th>
                <th>Importance</th>
                <th>Status</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {getFilteredEvents().map((event: any) => (
                <tr key={event.event_id}>
                  <td>
                    <span className="event-date">
                      {event.scheduled_at ? format(new Date(event.scheduled_at), 'MMM d, yyyy') : '-'}
                      {event.scheduled_at && event.released_at && (
                        <span className="release-time">
                          {format(new Date(event.released_at), 'HH:mm')}
                        </span>
                      )}
                    </span>
                  </td>
                  <td>
                    <Link to={`/search?q=${encodeURIComponent(event.title)}`} className="event-title-link">
                      {event.title}
                    </Link>
                  </td>
                  <td>
                    <Badge variant={getTypeBadgeVariant(event.event_type)}>
                      {event.event_type}
                    </Badge>
                  </td>
                  <td className={event.actual ? (event.forecast ? (parseFloat(event.actual) > parseFloat(event.forecast) ? 'positive' : 'negative') : '') : ''}>
                    {event.actual || '-'}
                  </td>
                  <td>{event.forecast || '-'}</td>
                  <td>{event.previous || '-'}</td>
                  <td>
                    <Badge variant={getImportanceBadgeVariant(event.importance)}>
                      {event.importance}
                    </Badge>
                  </td>
                  <td>
                    <Badge variant={getStatusBadgeVariant(event.status)}>
                      {event.status}
                    </Badge>
                  </td>
                  <td>
                    <a href={event.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                      {event.source}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {(!events || events.length === 0) && (
          <div className="empty-state">
            <div className="empty-state-icon">📅</div>
            <h3>No events found</h3>
            <p>Try adjusting your filters or check back later.</p>
          </div>
        )}
      </div>

      <div className="calendar-legend">
        <h4>Importance Levels</h4>
        <div className="legend-items">
          <div className="legend-item">
            <Badge variant="error">CRITICAL</Badge>
            <span>Market-moving events (FOMC, NFP, CPI)</span>
          </div>
          <div className="legend-item">
            <Badge variant="warning">HIGH</Badge>
            <span>Significant market impact expected</span>
          </div>
          <div className="legend-item">
            <Badge variant="secondary">MEDIUM</Badge>
            <span>Moderate market impact</span>
          </div>
          <div className="legend-item">
            <Badge variant="default">LOW</Badge>
            <span>Minor market impact</span>
          </div>
        </div>

        <div className="status-legend">
          <h4>Status</h4>
          <div className="legend-items">
            <span><Badge variant="success">RELEASED</Badge> - Data published</span>
            <span><Badge variant="secondary">SCHEDULED</Badge> - Upcoming</span>
            <span><Badge variant="warning">UPDATED</Badge> - Revised data</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function getImportanceBadgeVariant(importance: string) {
  switch (importance) {
    case 'CRITICAL': return 'error'
    case 'HIGH': return 'warning'
    case 'MEDIUM': return 'secondary'
    default: return 'default'
  }
}

function getStatusBadgeVariant(status: string) {
  switch (status) {
    case 'RELEASED': return 'success'
    case 'SCHEDULED': return 'secondary'
    case 'UPDATED': return 'warning'
    default: return 'default'
  }
}

function getTypeBadgeVariant(type: string) {
  const typeMap: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'error'> = {
    'FOMC': 'error',
    'CPI': 'error',
    'NFP': 'error',
    'PCE': 'error',
    'GDP': 'warning',
    'PPI': 'warning',
    'FOMC_MINUTES': 'warning',
    'JOLTS': 'secondary',
    'UNEMPLOYMENT': 'error',
    'RETAIL_SALES': 'warning',
    'HOUSING_STARTS': 'secondary',
    'BUILDING_PERMITS': 'secondary',
    'JOLTS': 'secondary',
    'AVG_HOURLY_EARNINGS': 'warning',
    'CONSUMER_CONFIDENCE': 'secondary',
    'ISM_MANUFACTURING': 'secondary',
    'ISM_SERVICES': 'secondary',
    'DURABLE_GOODS': 'secondary',
    'TRADE_BALANCE': 'secondary',
  }
  return typeMap[type] || 'default'
}

export default MacroCalendarPage