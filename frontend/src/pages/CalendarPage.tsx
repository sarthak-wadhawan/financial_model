import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../services/api'
import { Modal } from '../components/ui'
import type { CalendarExportRequest, CalendarExportResponse } from '../services/api'

const EVENT_TYPES = [
  { value: 'macro', label: 'Macro' },
  { value: 'earnings', label: 'Earnings' },
  { value: 'earnings_result', label: 'Earnings Result' },
  { value: 'earnings_guidance', label: 'Earnings Guidance' },
  { value: 'dividend', label: 'Dividend' },
  { value: 'stock_split', label: 'Stock Split' },
  { value: 'merger_acquisition', label: 'M&A' },
  { value: 'spinoff', label: 'Spinoff' },
  { value: 'corporate_action', label: 'Corporate Action' },
]

const IMPORTANCE_LEVELS = ['critical', 'high', 'medium', 'low']

export function CalendarPage() {
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportRequest, setExportRequest] = useState<CalendarExportRequest>({
    format: 'ics',
    event_types: undefined,
    symbols: undefined,
    from_date: undefined,
    to_date: undefined,
    importance: undefined,
  })
  const [exportResult, setExportResult] = useState<CalendarExportResponse | null>(null)

  const exportMutation = useMutation({
    mutationFn: (request: CalendarExportRequest) => api.exportCalendar(request),
    onSuccess: (result) => {
      setExportResult(result)
      // Auto-download the .ics file
      const blob = new Blob([result.content], { type: 'text/calendar;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
  })

  const handleExport = (e: React.FormEvent) => {
    e.preventDefault()
    if (exportRequest.from_date && exportRequest.to_date && exportRequest.from_date > exportRequest.to_date) return
    setExportResult(null)
    exportMutation.mutate(exportRequest)
  }

  const handleCheckboxChange = (name: string, value: string, checked: boolean) => {
    setExportRequest(prev => {
      const current = prev[name as keyof CalendarExportRequest] as string[] | undefined
      let updated: string[] = []
      if (checked) {
        updated = current ? [...current, value] : [value]
      } else {
        updated = current?.filter(v => v !== value) || []
      }
      return { ...prev, [name]: updated.length ? updated : undefined }
    })
  }

  const handleDateChange = (name: 'from_date' | 'to_date', value: string) => {
    setExportRequest(prev => ({ ...prev, [name]: value || undefined }))
  }

  return (
    <div className="page calendar-page">
      <div className="page-header">
        <h1>Calendar Export</h1>
        <p className="page-subtitle">Export events to calendar format (.ics)</p>
      </div>

      <div className="calendar-content">
        <div className="export-section">
          <h2>Export Events</h2>
          <p className="export-description">
            Export macro events, earnings, and company events to a standards-compliant iCalendar (.ics) file.
            The file can be imported into Google Calendar, Outlook, Apple Calendar, and other calendar applications.
          </p>

          <button className="btn btn-primary btn-lg" onClick={() => setShowExportModal(true)}>
            Export Calendar
          </button>

          {exportResult && (
            <div className="export-success">
              <h3>Export Complete!</h3>
              <p>Successfully exported {exportResult.event_count} events to <strong>{exportResult.filename}</strong></p>
              <p className="muted">The file should have downloaded automatically. If not, you can copy the content below.</p>
              <details className="export-content">
                <summary>View .ics content</summary>
                <pre>{exportResult.content}</pre>
              </details>
            </div>
          )}
        </div>

        <div className="info-section">
          <h3>Event Types Included</h3>
          <div className="event-types-grid">
            {EVENT_TYPES.map(({ value, label }) => (
              <div key={value} className="event-type-item">
                <span className="event-type-label">{label}</span>
                <span className="event-type-value">{value}</span>
              </div>
            ))}
          </div>

          <h3>Filter Options</h3>
          <ul className="filter-options">
            <li><strong>Event Types:</strong> Filter by macro events, earnings, dividends, splits, M&A, etc.</li>
            <li><strong>Symbols:</strong> Filter events for specific tickers (comma-separated)</li>
            <li><strong>Date Range:</strong> Export events within a specific date window</li>
            <li><strong>Importance:</strong> Filter by CRITICAL, HIGH, MEDIUM, LOW</li>
          </ul>

           <h3>Date and time precision</h3>
          <ul className="filter-options">
             <li><strong>Exact time:</strong> Source-supported timestamps are converted to UTC. No event duration is invented.</li>
             <li><strong>Date only:</strong> Exported as an all-day date, not a midnight release.</li>
             <li><strong>Unknown date or invalid event identity:</strong> Omitted from the calendar, never assigned today's date. Unsafe source links are not exported as clickable URLs; retained evidence is unchanged.</li>
            <li><strong>BMO/AMC Semantics:</strong> Before Market Open / After Market Close are preserved as session indicators, not exact times</li>
          </ul>
        </div>
      </div>

      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Export Calendar"
        size="lg"
      >
        <form onSubmit={handleExport}>
          <div className="form-section">
            <h3>Event Types</h3>
            <div className="checkbox-grid">
              {EVENT_TYPES.map(({ value, label }) => (
                <label key={value} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={exportRequest.event_types?.includes(value) || false}
                    onChange={(e) => handleCheckboxChange('event_types', value, e.target.checked)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-section">
            <label htmlFor="calendar-symbols">Symbols (Optional)</label>
            <input
              id="calendar-symbols"
              type="text"
              placeholder="AAPL, MSFT, GOOGL (comma-separated)"
              value={exportRequest.symbols?.join(', ') || ''}
              onChange={(e) => setExportRequest(prev => ({
                ...prev,
                symbols: e.target.value ? e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean) : undefined
              }))}
            />
            <p className="form-hint">Leave empty to include all symbols</p>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="from-date">From Date</label>
              <input
                id="from-date"
                type="date"
                value={exportRequest.from_date || ''}
                onChange={(e) => handleDateChange('from_date', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="to-date">To Date</label>
              <input
                id="to-date"
                type="date"
                value={exportRequest.to_date || ''}
                onChange={(e) => handleDateChange('to_date', e.target.value)}
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Importance Levels</h3>
            <div className="checkbox-grid">
              {IMPORTANCE_LEVELS.map((level) => (
                <label key={level} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={exportRequest.importance?.includes(level) || false}
                    onChange={(e) => handleCheckboxChange('importance', level, e.target.checked)}
                  />
                  <span>{level.toUpperCase()}</span>
                </label>
              ))}
            </div>
          </div>

          {exportRequest.from_date && exportRequest.to_date && exportRequest.from_date > exportRequest.to_date && <p role="alert" className="error-message">From date must not be after to date.</p>}
          {exportMutation.isError && <p role="alert" className="error-message">Calendar export failed. Check the filters and try again.</p>}
          <p className="form-hint">No checked boxes means all types/importance levels. Date bounds include the entire day.</p>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowExportModal(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={exportMutation.isPending}>
              {exportMutation.isPending ? 'Exporting...' : 'Export & Download .ics'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default CalendarPage
