import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { Tabs, Tab } from '../ui'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system')
  const [apiKeys, setApiKeys] = useState({})

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'api', label: 'API Keys' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'display', label: 'Display' },
    { id: 'data', label: 'Data Sources' },
  ]

  return (
    <div className="page settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Configure your Trading Copilot preferences</p>
      </div>

      <div className="settings-container">
        <aside className="settings-sidebar">
          <nav className="settings-nav" aria-label="Settings navigation">
            <Tabs
              tabs={tabs.map(t => ({ id: t.id, label: t.label }))}
              activeTab={activeTab}
              onChange={setActiveTab}
              variant="vertical"
            />
          </nav>
        </aside>

        <main className="settings-content">
          {activeTab === 'general' && <GeneralSettings />}
          {activeTab === 'api' && <ApiSettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
          {activeTab === 'display' && <DisplaySettings />}
          {activeTab === 'data' && <DataSettings />}
        </main>
      </div>
    </div>
  )
}

function GeneralSettings() {
  const [preferences, setPreferences] = useState({
    defaultSymbol: 'AAPL',
    defaultTimeframe: '1Day',
    autoRefresh: true,
    refreshInterval: 60,
    defaultTimezone: 'UTC',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setPreferences(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  return (
    <div className="settings-section">
      <section className="settings-group">
        <h3>Default Preferences</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="defaultSymbol">Default Symbol</label>
            <input
              type="text"
              id="defaultSymbol"
              name="defaultSymbol"
              value={preferences.defaultSymbol}
              onChange={handleChange}
              placeholder="AAPL"
            />
          </div>
          <div className="setting-item">
            <label htmlFor="defaultTimeframe">Default Timeframe</label>
            <select
              id="defaultTimeframe"
              name="defaultTimeframe"
              value={preferences.defaultTimeframe}
              onChange={handleChange}
            >
              <option value="1Min">1 Minute</option>
              <option value="5Min">5 Minutes</option>
              <option value="15Min">15 Minutes</option>
              <option value="1Hour">1 Hour</option>
              <option value="1Day" selected>1 Day</option>
              <option value="1Week">1 Week</option>
              <option value="1Month">1 Month</option>
            </select>
          </div>
          <div className="setting-item">
            <label htmlFor="defaultTimezone">Default Timezone</label>
            <select
              id="defaultTimezone"
              name="defaultTimezone"
              value={preferences.defaultTimezone}
              onChange={handleChange}
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time</option>
              <option value="America/Chicago">Central Time</option>
              <option value="America/Denver">Mountain Time</option>
              <option value="America/Los_Angeles">Pacific Time</option>
              <option value="Europe/London">London</option>
              <option value="Asia/Tokyo">Tokyo</option>
            </select>
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Behavior</h3>
        <div className="settings-list">
          <label className="setting-toggle">
            <input
              type="checkbox"
              name="autoRefresh"
              checked={preferences.autoRefresh}
              onChange={handleChange}
            />
            <span>Auto-refresh data</span>
          </label>
          <div className="setting-item">
            <label htmlFor="refreshInterval">Refresh Interval (seconds)</label>
            <input
              type="number"
              id="refreshInterval"
              name="refreshInterval"
              value={preferences.refreshInterval}
              onChange={handleChange}
              min={10}
              max={3600}
              step={10}
            />
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Default Symbol</h3>
        <div className="setting-item">
          <input
            type="text"
            name="defaultSymbol"
            value={preferences.defaultSymbol}
            onChange={handleChange}
            placeholder="AAPL"
            style={{ textTransform: 'uppercase' }}
          />
        </div>
      </section>
    </div>
  )
}

function ApiSettings() {
  const [apiKeys, setApiKeys] = useState({
    alpaca: { key: '', secret: '' },
    alphaVantage: '',
    polygon: '',
    twelveData: '',
    finnhub: '',
  })
  const [testing, setTesting] = useState<string | null>(null)

  const handleKeyChange = (provider: string, field: 'key' | 'secret', value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [provider]: { ...prev[provider], [field]: value },
    }))
  }

  const testConnection = async (provider: string) => {
    // TODO: Implement API connection test
    alert(`Testing ${provider} connection...`)
  }

  const providers = [
    {
      id: 'alpaca',
      name: 'Alpaca Markets',
      description: 'Market data (IEX feed), paper trading',
      fields: ['key', 'secret'],
      docsUrl: 'https://alpaca.markets/docs/',
    },
    {
      id: 'alphaVantage',
      name: 'Alpha Vantage',
      description: 'Earnings, fundamentals, technical indicators',
      fields: ['key'],
      docsUrl: 'https://www.alphavantage.co/documentation/',
    },
    {
      id: 'polygon',
      name: 'Polygon.io',
      description: 'Real-time & historical market data',
      fields: ['key'],
      docsUrl: 'https://polygon.io/docs/',
    },
    {
      id: 'twelveData',
      name: 'Twelve Data',
      description: 'Stock, forex, crypto data',
      fields: ['key'],
      docsUrl: 'https://twelvedata.com/docs',
    },
    {
      id: 'finnhub',
      name: 'Finnhub',
      description: 'Real-time stock data, news, filings',
      fields: ['key'],
      docsUrl: 'https://finnhub.io/docs/api',
    },
  ]

  return (
    <div className="settings-section">
      <section className="settings-group">
        <h3>API Providers</h3>
        <p className="settings-description">
          Configure API keys for additional data sources. Keys are stored securely and never exposed to the frontend.
        </p>
        <div className="providers-grid">
          {providers.map(provider => (
            <div key={provider.id} className="provider-card">
              <div className="provider-header">
                <h4>{provider.name}</h4>
                <p className="provider-description">{provider.description}</p>
              </div>
              <div className="provider-fields">
                {provider.fields.map(field => (
                  <div key={field} className="setting-item">
                    <label htmlFor={`${provider.id}-${field}`}>
                      {field === 'key' ? 'API Key' : 'Secret Key'}
                    </label>
                    <input
                      type="password"
                      id={`${provider.id}-${field}`}
                      name={`${provider.id}-${field}`}
                      value={apiKeys[provider.id]?.[field] || ''}
                      onChange={e => handleKeyChange(provider.id, field as 'key' | 'secret', e.target.value)}
                      placeholder={`Enter ${provider.name} ${field}`}
                    />
                  </div>
                ))}
              </div>
              <div className="provider-actions">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => testConnection(provider.id)}
                  disabled={testing === provider.id}
                >
                  {testing === provider.id ? 'Testing...' : 'Test Connection'}
                </button>
                <a
                  href={provider.docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-link btn-sm"
                >
                  View Docs
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="settings-group">
        <h3>Security</h3>
        <div className="settings-list">
          <label className="setting-toggle">
            <input type="checkbox" name="encryptKeys" checked={true} />
            <span>Encrypt API keys at rest</span>
          </label>
          <label className="setting-toggle">
            <input type="checkbox" name="requireAuth" checked={true} />
            <span>Require authentication for API access</span>
          </label>
        </div>
      </section>
    </div>
  )
}

function NotificationSettings() {
  const [prefs, setPrefs] = useState({
    emailAlerts: true,
    priceAlerts: true,
    earningsAlerts: true,
    newsAlerts: false,
    macroAlerts: true,
    insiderAlerts: false,
    digestFrequency: 'daily',
    quietHours: { enabled: false, start: '22:00', end: '07:00' },
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setPrefs(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  return (
    <div className="settings-section">
      <section className="settings-group">
        <h3>Alert Types</h3>
        <div className="settings-list">
          {[
            { id: 'emailAlerts', label: 'Email notifications' },
            { id: 'priceAlerts', label: 'Price alerts' },
            { id: 'earningsAlerts', label: 'Earnings alerts' },
            { id: 'newsAlerts', label: 'Breaking news' },
            { id: 'macroAlerts', label: 'Macro events' },
            { id: 'insiderAlerts', label: 'Insider transactions' },
          ].map(item => (
            <label key={item.id} className="setting-toggle">
              <input
                type="checkbox"
                name={item.id}
                checked={prefs[item.id as keyof typeof prefs]}
                onChange={e => setPrefs(prev => ({ ...prev, [item.id]: e.target.checked }))}
              />
              <span>{item.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="settings-group">
        <h3>Delivery</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="digestFrequency">Digest Frequency</label>
            <select
              id="digestFrequency"
              name="digestFrequency"
              value={prefs.digestFrequency}
              onChange={e => setPrefs(prev => ({ ...prev, digestFrequency: e.target.value }))}
            >
              <option value="instant">Instant</option>
              <option value="hourly">Hourly</option>
              <option value="daily" selected>Daily digest</option>
              <option value="weekly">Weekly digest</option>
            </select>
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Quiet Hours</h3>
        <div className="settings-grid">
          <label className="setting-toggle">
            <input
              type="checkbox"
              name="quietHours.enabled"
              checked={prefs.quietHours.enabled}
              onChange={e => setPrefs(prev => ({ ...prev, quietHours: { ...prev.quietHours, enabled: e.target.checked } }))}
            />
            <span>Enable quiet hours</span>
          </label>
          <div className="setting-item">
            <label htmlFor="quietStart">Start</label>
            <input
              type="time"
              id="quietStart"
              name="quietHours.start"
              value={prefs.quietHours.start}
              onChange={e => setPrefs(prev => ({ ...prev, quietHours: { ...prev.quietHours, start: e.target.value } }))}
              disabled={!prefs.quietHours.enabled}
            />
          </div>
          <div className="setting-item">
            <label htmlFor="quietEnd">End</label>
            <input
              type="time"
              id="quietEnd"
              name="quietHours.end"
              value={prefs.quietHours.end}
              onChange={e => setPrefs(prev => ({ ...prev, quietHours: { ...prev.quietHours, end: e.target.value } }))}
              disabled={!prefs.quietHours.enabled}
            />
          </div>
        </div>
      </section>
    </div>
  )
}

function DisplaySettings() {
  const [prefs, setPrefs] = useState({
    theme: 'system' as 'light' | 'dark' | 'system',
    compactMode: false,
    showSidebar: true,
    showQuantScores: true,
    chartType: 'candlestick' as 'line' | 'candlestick' | 'area',
    pricePrecision: 2,
    volumeFormat: 'compact' as 'compact' | 'full',
    dateFormat: 'MMM d, yyyy',
    timeFormat: '24h' as '12h' | '24h',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setPrefs(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  return (
    <div className="settings-section">
      <section className="settings-group">
        <h3>Theme & Layout</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="theme">Theme</label>
            <select
              id="theme"
              name="theme"
              value={prefs.theme}
              onChange={handleChange}
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>
          <div className="setting-item">
            <label htmlFor="compactMode">Compact Mode</label>
            <label className="setting-toggle">
              <input
                type="checkbox"
                name="compactMode"
                checked={prefs.compactMode}
                onChange={handleChange}
              />
              <span>Compact mode (denser tables)</span>
            </label>
          </div>
          <div className="setting-item">
            <label htmlFor="showSidebar">Show Sidebar</label>
            <label className="setting-toggle">
              <input
                type="checkbox"
                name="showSidebar"
                checked={prefs.showSidebar}
                onChange={handleChange}
              />
              <span>Show sidebar navigation</span>
            </label>
          </div>
          <div className="setting-item">
            <label htmlFor="showQuantScores">Show Quant Scores</label>
            <label className="setting-toggle">
              <input
                type="checkbox"
                name="showQuantScores"
                checked={prefs.showQuantScores}
                onChange={handleChange}
              />
              <span>Show quant scores on dashboard</span>
            </label>
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Charts</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="chartType">Default Chart Type</label>
            <select
              id="chartType"
              name="chartType"
              value={prefs.chartType}
              onChange={handleChange}
            >
              <option value="candlestick">Candlestick</option>
              <option value="line">Line</option>
              <option value="area">Area</option>
            </select>
          </div>
          <div className="setting-item">
            <label htmlFor="pricePrecision">Price Precision</label>
            <select
              id="pricePrecision"
              name="pricePrecision"
              value={prefs.pricePrecision}
              onChange={handleChange}
            >
              <option value="0">0 decimals</option>
              <option value="1">1 decimal</option>
              <option value="2" selected>2 decimals</option>
              <option value="3">3 decimals</option>
              <option value="4">4 decimals</option>
            </select>
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Data Display</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="volumeFormat">Volume Format</label>
            <select
              id="volumeFormat"
              name="volumeFormat"
              value={prefs.volumeFormat}
              onChange={handleChange}
            >
              <option value="compact">Compact (1.2M)</option>
              <option value="full">Full (1,234,567)</option>
            </select>
          </div>
          <div className="setting-item">
            <label htmlFor="dateFormat">Date Format</label>
            <select
              id="dateFormat"
              name="dateFormat"
              value={prefs.dateFormat}
              onChange={handleChange}
            >
              <option value="MMM d, yyyy">Jan 15, 2024</option>
              <option value="yyyy-MM-dd">2024-01-15</option>
              <option value="d/M/yyyy">15/01/2024</option>
            </select>
          </div>
          <div className="setting-item">
            <label htmlFor="timeFormat">Time Format</label>
            <select
              id="timeFormat"
              name="timeFormat"
              value={prefs.timeFormat}
              onChange={handleChange}
            >
              <option value="12h">12-hour (3:30 PM)</option>
              <option value="24h" selected>24-hour (15:30)</option>
            </select>
          </div>
        </div>
      </section>
    </div>
  )
}

function DataSettings() {
  const [prefs, setPrefs] = useState({
    cacheTTL: 300,
    maxHistoryDays: 365,
    autoFetchNews: true,
    autoFetchEarnings: true,
    autoFetchFilings: true,
    cacheStrategy: 'smart' as 'aggressive' | 'smart' | 'minimal',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setPrefs(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  return (
    <div className="settings-section">
      <section className="settings-group">
        <h3>Caching</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="cacheTTL">Cache TTL (seconds)</label>
            <input
              type="number"
              id="cacheTTL"
              name="cacheTTL"
              value={prefs.cacheTTL}
              onChange={handleChange}
              min={60}
              max={86400}
              step={60}
            />
          </div>
          <div className="setting-item">
            <label htmlFor="maxHistoryDays">Max History Days</label>
            <input
              type="number"
              id="maxHistoryDays"
              name="maxHistoryDays"
              value={prefs.maxHistoryDays}
              onChange={handleChange}
              min={30}
              max={3650}
            />
          </div>
        </div>
      </section>

      <section className="settings-group">
        <h3>Auto-Fetch</h3>
        <div className="settings-list">
          <label className="setting-toggle">
            <input
              type="checkbox"
              name="autoFetchNews"
              checked={prefs.autoFetchNews}
              onChange={handleChange}
            />
            <span>Auto-fetch news</span>
          </label>
          <label className="setting-toggle">
            <input
              type="checkbox"
              name="autoFetchEarnings"
              checked={prefs.autoFetchEarnings}
              onChange={handleChange}
            />
            <span>Auto-fetch earnings</span>
          </label>
          <label className="setting-toggle">
            <input
              type="checkbox"
              name="autoFetchFilings"
              checked={prefs.autoFetchFilings}
              onChange={handleChange}
            />
            <span>Auto-fetch SEC filings</span>
          </label>
        </div>
      </section>

      <section className="settings-group">
        <h3>Cache Strategy</h3>
        <div className="setting-item">
          <label htmlFor="cacheStrategy">Strategy</label>
          <select
            id="cacheStrategy"
            name="cacheStrategy"
            value={prefs.cacheStrategy}
            onChange={e => setPrefs(prev => ({ ...prev, cacheStrategy: e.target.value }))}
          >
            <option value="aggressive">Aggressive (cache everything)</option>
            <option value="smart" selected>Smart (cache frequently accessed)</option>
            <option value="minimal">Minimal (cache only essentials)</option>
          </select>
        </div>
      </section>

      <section className="settings-group">
        <h3>Data Retention</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <label htmlFor="newsRetention">News Retention (days)</label>
            <input
              type="number"
              id="newsRetention"
              name="newsRetention"
              value={30}
              onChange={e => console.log(e.target.value)}
              min={1}
              max={365}
            />
          </div>
          <div className="setting-item">
            <label htmlFor="eventsRetention">Events Retention (days)</label>
            <input
              type="number"
              id="eventsRetention"
              name="eventsRetention"
              value={90}
              onChange={e => console.log(e.target.value)}
              min={7}
              max={730}
            />
          </div>
        </div>
      </section>
    </div>
  )
}

export default SettingsPage