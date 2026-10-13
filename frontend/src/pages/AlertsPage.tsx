import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { api } from '../services/api'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { Badge, Modal, ConfirmDialog } from '../components/ui'
import type { AlertCreate, AlertUpdate } from '../services/api'

const ALERT_TYPES = [
  { value: 'price', label: 'Price' },
  { value: 'price_change_pct', label: 'Price Change %' },
  { value: 'volume', label: 'Volume' },
  { value: 'earnings', label: 'Earnings' },
  { value: 'earnings_surprise', label: 'Earnings Surprise' },
  { value: 'guidance_change', label: 'Guidance Change' },
  { value: 'filing', label: 'SEC Filing' },
  { value: 'insider', label: 'Insider Transaction' },
  { value: 'leadership', label: 'Leadership Change' },
  { value: 'news', label: 'News' },
  { value: 'macro_event', label: 'Macro Event' },
  { value: 'quant_score', label: 'Quant Score' },
]

const CONDITIONS = [
  { value: 'above', label: 'Above' },
  { value: 'below', label: 'Below' },
  { value: 'equals', label: 'Equals' },
  { value: 'crosses_above', label: 'Crosses Above' },
  { value: 'crosses_below', label: 'Crosses Below' },
  { value: 'changes', label: 'Changes' },
]

const SEVERITIES = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
]

const CHANNELS = [
  { value: 'in_app' as const, label: 'In-App' },
  { value: 'email' as const, label: 'Email' },
  { value: 'webhook' as const, label: 'Webhook' },
]

export function AlertsPage() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'triggered'>('all')

  const [newAlert, setNewAlert] = useState<AlertCreate>({
    name: '',
    alert_type: 'price',
    symbols: [],
    condition: 'above',
    threshold: null,
    severity: 'warning',
    channels: ['in_app'],
    is_active: true,
    cooldown_minutes: 60,
  })

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(),
    staleTime: 1000 * 60 * 5,
  })

  const { data: recentTriggers } = useQuery({
    queryKey: ['alertTriggers', 'recent'],
    queryFn: () => api.getRecentAlertTriggers(24, 50),
    staleTime: 1000 * 60 * 5,
  })

  const createMutation = useMutation({
    mutationFn: (alert: AlertCreate) => api.createAlert(alert),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      setShowCreateModal(false)
      setNewAlert({
        name: '',
        alert_type: 'price',
        symbols: [],
        condition: 'above',
        threshold: null,
        severity: 'warning',
        channels: ['in_app'],
        is_active: true,
        cooldown_minutes: 60,
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: string; update: AlertUpdate }) => api.updateAlert(id, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      setShowDeleteConfirm(null)
    },
  })

  const testMutation = useMutation({
    mutationFn: (request: { alert_id: string }) => api.testAlert(request),
    onSuccess: (result) => {
      alert(result.message || (result.would_trigger ? 'Alert would trigger!' : 'Alert would not trigger'))
    },
  })

  const filteredAlerts = alerts?.filter(a => {
    if (activeTab === 'active') return a.is_active
    if (activeTab === 'triggered') return !a.is_active
    return true
  }) || []

  if (alertsLoading) {
    return (
      <div className="page alerts-page">
        <div className="page-header">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  return (
    <div className="page alerts-page">
      <div className="page-header">
        <div className="page-header-content">
          <h1>Alerts</h1>
          <p className="page-subtitle">Configure price, volume, earnings, and event alerts</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          Create Alert
        </button>
      </div>

      <div className="alerts-tabs">
        <button
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All ({alerts?.length || 0})
        </button>
        <button
          className={`tab ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          Active ({alerts?.filter(a => a.is_active).length || 0})
        </button>
        <button
          className={`tab ${activeTab === 'triggered' ? 'active' : ''}`}
          onClick={() => setActiveTab('triggered')}
        >
          Triggered ({recentTriggers?.length || 0})
        </button>
      </div>

      {filteredAlerts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔔</div>
          <h3>No alerts found</h3>
          <p>Create your first alert to get notified about market events</p>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Create Alert
          </button>
        </div>
      ) : (
        <div className="alerts-list">
          {filteredAlerts.map((alert) => (
            <div key={alert.id} className="alert-card">
              <div className="alert-header">
                <div className="alert-info">
                  <h3>{alert.name}</h3>
                  <div className="alert-meta">
                    <Badge variant={alert.is_active ? 'success' : 'default'}>
                      {alert.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    <Badge variant="secondary">{alert.alert_type}</Badge>
                    <Badge variant="secondary">{alert.condition}</Badge>
                    {alert.threshold !== null && (
                      <Badge variant="secondary">
                        {alert.condition} {alert.threshold}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="alert-actions">
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => updateMutation.mutate({ id: alert.id, update: { is_active: !alert.is_active } })}
                  >
                    {alert.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => testMutation.mutate({ alert_id: alert.id })}
                  >
                    Test
                  </button>
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => setShowDeleteConfirm(alert.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="alert-details">
                <div className="detail-row">
                  <span className="detail-label">Symbols:</span>
                  <span>{alert.symbols.join(', ') || 'All symbols'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Severity:</span>
                  <Badge variant={alert.severity === 'critical' ? 'error' : alert.severity}>{alert.severity}</Badge>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Channels:</span>
                  <span>{alert.channels.join(', ')}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Cooldown:</span>
                  <span>{alert.cooldown_minutes} min</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Triggered:</span>
                  <span>{alert.trigger_count} times</span>
                </div>
                {alert.last_triggered && (
                  <div className="detail-row">
                    <span className="detail-label">Last Triggered:</span>
                    <span>{format(new Date(alert.last_triggered), 'MMM d, yyyy HH:mm')}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'triggered' && (
        <div className="trigger-history-section">
          <h3>Recent Triggers</h3>
          {recentTriggers?.length === 0 ? (
            <p className="muted">No recent triggers</p>
          ) : (
            <div className="trigger-history-list">
              {recentTriggers?.map((trigger) => (
                <div key={trigger.id} className="trigger-item">
                  <div className="trigger-header">
                    <span className="trigger-symbol">{trigger.symbol}</span>
                    <Badge variant={(trigger.severity === 'critical' ? 'error' : trigger.severity) as 'default' | 'success' | 'error' | 'warning' | 'info' | 'primary' | 'secondary'}>{trigger.severity}</Badge>
                  </div>
                  <p className="trigger-message">{trigger.message}</p>
                  <div className="trigger-meta">
                    <span>Value: {trigger.value?.toFixed(2)}</span>
                    <span>Threshold: {trigger.threshold?.toFixed(2)}</span>
                    <span>{format(new Date(trigger.triggered_at), 'MMM d, yyyy HH:mm')}</span>
                  </div>
                  {!trigger.acknowledged && (
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => {
                        api.acknowledgeAlertTrigger(trigger.id)
                        queryClient.invalidateQueries({ queryKey: ['alertTriggers'] })
                      }}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Alert"
        size="lg"
      >
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(newAlert) }}>
          <div className="form-section">
            <h3>Basic Settings</h3>
            <div className="form-group">
              <label htmlFor="alert-name">Alert Name</label>
              <input
                id="alert-name"
                type="text"
                value={newAlert.name}
                onChange={(e) => setNewAlert({ ...newAlert, name: e.target.value })}
                placeholder="AAPL Price Alert"
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label htmlFor="alert-description">Description (optional)</label>
              <textarea
                id="alert-description"
                value={newAlert.description || ''}
                onChange={(e) => setNewAlert({ ...newAlert, description: e.target.value })}
                placeholder="Optional description"
                rows={2}
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Alert Configuration</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="alert-type">Alert Type</label>
                <select
                  id="alert-type"
                  value={newAlert.alert_type}
                  onChange={(e) => setNewAlert({ ...newAlert, alert_type: e.target.value })}
                >
                  {ALERT_TYPES.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="alert-condition">Condition</label>
                <select
                  id="alert-condition"
                  value={newAlert.condition}
                  onChange={(e) => setNewAlert({ ...newAlert, condition: e.target.value })}
                >
                  {CONDITIONS.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="alert-threshold">Threshold</label>
                <input
                  id="alert-threshold"
                  type="number"
                  step="0.01"
                  value={newAlert.threshold?.toString() || ''}
                  onChange={(e) => setNewAlert({ ...newAlert, threshold: e.target.value ? parseFloat(e.target.value) : null })}
                  placeholder="e.g., 200"
                />
              </div>
              <div className="form-group">
                <label htmlFor="alert-severity">Severity</label>
                <select
                  id="alert-severity"
                  value={newAlert.severity}
                  onChange={(e) => setNewAlert({ ...newAlert, severity: e.target.value as 'info' | 'warning' | 'critical' })}
                >
                  {SEVERITIES.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Symbols</h3>
            <input
              type="text"
              placeholder="AAPL, MSFT, GOOGL (comma-separated, leave empty for all)"
              value={newAlert.symbols.join(', ')}
              onChange={(e) => setNewAlert({ ...newAlert, symbols: e.target.value ? e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean) : [] })}
            />
            <p className="form-hint">Leave empty to monitor all symbols</p>
          </div>

          <div className="form-section">
            <h3>Notification Channels</h3>
            <div className="checkbox-grid">
              {CHANNELS.map(({ value, label }) => {
                const channelValue = value as 'in_app' | 'email' | 'webhook'
                return (
                  <label key={value} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={(newAlert.channels || []).includes(channelValue)}
                      onChange={(e) => setNewAlert({
                        ...newAlert,
                        channels: e.target.checked
                          ? [...(newAlert.channels || []), channelValue]
                          : (newAlert.channels || []).filter(c => c !== channelValue)
                      })}
                    />
                    <span>{label}</span>
                  </label>
                )
              })}
            </div>
            <p className="form-hint muted">
              <strong>Note:</strong> Email and Webhook channels require backend delivery infrastructure.
              Currently only In-App notifications are delivered.
            </p>
          </div>

          <div className="form-section">
            <h3>Advanced</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="cooldown">Cooldown (minutes)</label>
                <input
                  id="cooldown"
                  type="number"
                  min="1"
                  value={newAlert.cooldown_minutes}
                  onChange={(e) => setNewAlert({ ...newAlert, cooldown_minutes: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Alert'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(null)}
        onConfirm={() => deleteMutation.mutate(showDeleteConfirm!)}
        title="Delete Alert"
        message="Are you sure you want to delete this alert? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

export default AlertsPage