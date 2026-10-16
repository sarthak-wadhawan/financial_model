import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { Badge, Tabs } from '../components/ui'
import { api } from '../services/api'
import { DataStatus, eventDate, EventTiming, ProviderCoverage, SourceLink } from '../components/ui/ResearchData'
import type { MacroEventResponse } from '../services/api'

export function MacroCalendarPage() {
  const { data: events, isLoading, isError, refetch } = useQuery({
    queryKey: ['macroEvents', 'all'],
    queryFn: () => api.getMacroEvents({ limit: 100 }),
    staleTime: 1000 * 60 * 5,
  })

  const [filterImportance, setFilterImportance] = useState<string>('all')
  const [filterType, setFilterType] = useState<string>('all')
  const [activeTab, setActiveTab] = useState<string>('upcoming')

  const filteredEvents = useMemo(() => {
    return events?.filter((e: MacroEventResponse) => {
      if (filterImportance !== 'all' && e.importance.toUpperCase() !== filterImportance) return false
      if (filterType !== 'all' && e.event_type.toUpperCase() !== filterType) return false
      return true
    }) || []
  }, [events, filterImportance, filterType])

  const getFilteredEvents = useMemo(() => {
    const base = filteredEvents
    switch (activeTab) {
      case 'upcoming':
        return base.filter((e: MacroEventResponse) => !e.released_at && ['SCHEDULED', 'UPDATED'].includes(e.status.toUpperCase()) && (!eventDate(e) || eventDate(e)!.slice(0, 10) >= new Date().toISOString().slice(0, 10)))
      case 'recent':
        return base.filter((e: MacroEventResponse) => !!e.released_at || e.status.toUpperCase() === 'RELEASED')
      default:
        return base
    }
  }, [filteredEvents, activeTab])

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
            id="importance-filter"
            value={filterImportance}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterImportance(e.target.value)}
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
            id="type-filter"
            value={filterType}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterType(e.target.value)}
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

      <ProviderCoverage />

      <DataStatus error={isError} label="macro events" />
      {isError && <button className="btn btn-secondary" onClick={() => refetch()}>Retry macro events</button>}
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

        <div className="events-table-container" id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`} tabIndex={0}>
          <table className="events-table">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Event</th>
                <th scope="col">Type</th>
                <th scope="col">Actual</th>
                <th scope="col">Forecast</th>
                <th scope="col">Previous</th>
                <th scope="col">Importance</th>
                <th scope="col">Status</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              {getFilteredEvents.map((event) => (
                <tr key={event.event_id}>
                  <td>
                    <span className="event-date">
                      <EventTiming event={event} />
                      {event.released_at && (
                        <span className="release-time">
                          Released (as supplied): {event.released_at}
                        </span>
                      )}
                    </span>
                  </td>
                  <td>
                    {event.title}
                  </td>
                  <td>
                    <Badge variant={getTypeBadgeVariant(event.event_type)}>
                      {event.event_type}
                    </Badge>
                  </td>
                  <td>
                    {event.actual ?? 'Unknown'}
                  </td>
                  <td>{event.forecast ?? 'Unknown'}</td>
                  <td>{event.previous ?? 'Unknown'}</td>
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
                    <SourceLink url={event.source_url}>{event.source}</SourceLink>
                    {/(test|fixture|mock|demo)/i.test(event.source) && <small> — test/demo provenance, not live</small>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!isError && getFilteredEvents.length === 0 && (
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
  switch (importance.toUpperCase()) {
    case 'CRITICAL': return 'error'
    case 'HIGH': return 'warning'
    case 'MEDIUM': return 'secondary'
    default: return 'default'
  }
}

function getStatusBadgeVariant(status: string) {
  switch (status.toUpperCase()) {
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
    'AVG_HOURLY_EARNINGS': 'warning',
    'CONSUMER_CONFIDENCE': 'secondary',
    'ISM_MANUFACTURING': 'secondary',
    'ISM_SERVICES': 'secondary',
    'DURABLE_GOODS': 'secondary',
    'TRADE_BALANCE': 'secondary',
  }
  return typeMap[type.toUpperCase()] || 'default'
}

export default MacroCalendarPage
