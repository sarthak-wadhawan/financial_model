import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    this.client.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle auth errors
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, {
      params: { timeframe, start, end, limit }
    })
  }

  async refreshMarketData(symbols: string[]) {
    return this.post<{ status: string; symbols: string[]; state: Record<string, unknown> }>('/market/refresh', { symbols }, { timeout: 300000 })
  }

  async getProviderCoverage() {
    return this.get<{ providers: Record<string, unknown> }>('/health/detailed')
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', {
      params: { q: query, limit }
    })
  }

  // Stock detail
  async getStockDetail(symbol: string) {
    return this.get<StockDetail>(`/stocks/${symbol}`)
  }

  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, {
      params: { as_of: asOf }
    })
  }

  async answerQuestion(symbol: string, question: string, context?: Record<string, unknown>) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question, context })
  }

  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, {
      params: { event_types: eventTypes?.join(','), limit }
    })
  }

  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, {
      params: { limit, from_date: fromDate, to_date: toDate }
    })
  }

  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, {
      params: { limit }
    })
  }

  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  async getQuantScannerTop(n: number) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  async getScannerStatus() {
    return this.get<DataAvailability & { calculated_at: string | null; universe_size: number }>('/scanner/status')
  }

  // Macro events
  async getMacroEvents(params?: {
    from_date?: string
    to_date?: string
    importance?: string
    limit?: number
  }) {
    return this.get<MacroEventResponse[]>('/events/macro', { params })
  }

  async getUpcomingEvents(days?: number, limit?: number) {
    return this.get<UpcomingEventResponse[]>('/events/upcoming', {
      params: { days, limit }
    })
  }

  async getRecentEvents(days?: number, limit?: number) {
    return this.get<Event[]>('/events/recent', { params: { days, limit } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Phase 11: Watchlists
  async getWatchlists() {
    return this.get<Watchlist[]>('/watchlists')
  }

  async getWatchlist(watchlistId: string) {
    return this.get<WatchlistWithItems>(`/watchlists/${watchlistId}`)
  }

  async createWatchlist(watchlist: WatchlistCreate) {
    return this.post<Watchlist>('/watchlists', watchlist)
  }

  async updateWatchlist(watchlistId: string, update: WatchlistUpdate) {
    return this.patch<Watchlist>(`/watchlists/${watchlistId}`, update)
  }

  async deleteWatchlist(watchlistId: string) {
    return this.delete<void>(`/watchlists/${watchlistId}`)
  }

  async setDefaultWatchlist(watchlistId: string) {
    return this.post<Watchlist>(`/watchlists/${watchlistId}/set-default`)
  }

  async getWatchlistItems(watchlistId: string) {
    return this.get<WatchlistItem[]>(`/watchlists/${watchlistId}/items`)
  }

  async addWatchlistItem(watchlistId: string, item: WatchlistItemCreate) {
    return this.post<WatchlistItem>(`/watchlists/${watchlistId}/items`, item)
  }

  async updateWatchlistItem(watchlistId: string, symbol: string, update: WatchlistItemUpdate) {
    return this.patch<WatchlistItem>(`/watchlists/${watchlistId}/items/${symbol}`, update)
  }

  async removeWatchlistItem(watchlistId: string, symbol: string) {
    return this.delete<void>(`/watchlists/${watchlistId}/items/${symbol}`)
  }

  async reorderWatchlistItems(watchlistId: string, symbols: string[]) {
    return this.post<void>(`/watchlists/${watchlistId}/reorder`, { symbols })
  }

  async getWatchlistSymbols(watchlistId: string) {
    return this.get<string[]>(`/watchlists/${watchlistId}/symbols`)
  }

  async getWatchlistsForSymbol(symbol: string) {
    return this.get<Watchlist[]>(`/watchlists/symbol/${symbol}`)
  }

  // Phase 11: Calendar
  async exportCalendar(request: CalendarExportRequest) {
    return this.post<CalendarExportResponse>('/calendar/export', request)
  }

  async exportCalendarGet(params: {
    format?: string
    event_types?: string
    symbols?: string
    from_date?: string
    to_date?: string
    importance?: string
  }) {
    return this.get<CalendarExportResponse>('/calendar/export', { params })
  }

  // Phase 11: Alerts
  async getAlerts(activeOnly?: boolean) {
    return this.get<Alert[]>('/alerts', { params: { active_only: activeOnly } })
  }

  async getAlert(alertId: string) {
    return this.get<Alert>(`/alerts/${alertId}`)
  }

  async createAlert(alert: AlertCreate) {
    return this.post<Alert>('/alerts', alert)
  }

  async updateAlert(alertId: string, update: AlertUpdate) {
    return this.patch<Alert>(`/alerts/${alertId}`, update)
  }

  async deleteAlert(alertId: string) {
    return this.delete<void>(`/alerts/${alertId}`)
  }

  async activateAlert(alertId: string) {
    return this.post<Alert>(`/alerts/${alertId}/activate`)
  }

  async deactivateAlert(alertId: string) {
    return this.post<Alert>(`/alerts/${alertId}/deactivate`)
  }

  async testAlert(request: AlertTestRequest) {
    return this.post<AlertTestResponse>('/alerts/test', request)
  }

  async evaluateAlert(alertId: string) {
    return this.post<AlertEvaluationResponse>(`/alerts/${alertId}/evaluate`)
  }

  async getAlertTriggers(alertId: string, limit?: number, unacknowledgedOnly?: boolean) {
    return this.get<AlertTrigger[]>(`/alerts/${alertId}/triggers`, {
      params: { limit, unacknowledged_only: unacknowledgedOnly }
    })
  }

  async getRecentAlertTriggers(hours?: number, limit?: number) {
    return this.get<AlertTrigger[]>('/alerts/triggers/recent', {
      params: { hours, limit }
    })
  }

  async acknowledgeAlertTrigger(triggerId: string) {
    return this.post<void>(`/alerts/triggers/${triggerId}/acknowledge`)
  }

  async acknowledgeAllAlertTriggers(alertId: string) {
    return this.post<{ acknowledged: number }>(`/alerts/${alertId}/triggers/acknowledge-all`)
  }
}

export const api = new ApiClient()

// Type definitions for API responses
export interface MarketOverviewResponse {
  timestamp: string
  mode: 'real' | 'demo'
  source: string
  source_url: string | null
  reason: string | null
  market_data_status: string
  quant_scanner_status: string
  market_status: string
  snapshot_time: string | null
  symbols_tracked: number
  indices: Array<{
    symbol: string
    status?: string
    reason?: string | null
    price: number | null
    change: number | null
    change_pct: number | null
    market_timestamp: string | null
    retrieved_at: string | null
    source: string | null
    source_url?: string | null
    price_kind: string | null
  }>
  top_gainers: Array<{
    symbol: string
    price: number
    change_pct: number
  }>
  top_losers: Array<{
    symbol: string
    price: number
    change_pct: number
  }>
  most_active: Array<{
    symbol: string
    price: number
    volume: number
  }>
}

export interface DataAvailability {
  status: string
  reason: string | null
  mode: 'real' | 'demo'
  source: string
  source_url?: string | null
  market_timestamp?: string | null
  retrieved_at?: string | null
}

export interface BarData extends DataAvailability {
  symbol: string
  timeframe: string
  bars: Array<{
    t: string
    o: number
    h: number
    l: number
    c: number
    v: number
  }>
}

export interface SymbolSearchResult {
  symbol: string
  name: string | null
  exchange: string | null
  type: string
  source: string
}

export interface StockDetail {
  symbol: string
  name: string | null
  exchange: string | null
  price: number | null
  change: number | null
  change_pct: number | null
  volume: number | null
  market_cap: number | null
  pe_ratio: number | null
  dividend_yield: number | null
  price_data: DataAvailability & { price_kind: string }
  quant_signals: QuantSignals
  interpretation: Interpretation
  events: CompanyEvent[]
}

export interface Interpretation {
  interpretation_id: string
  symbol: string
  as_of: string
  headline: string
  what_happened: string
  what_it_means: string
  why_it_matters: string
  company_impact: {
    direction: string
    magnitude: string
    horizon: string
    confidence: number
    reasons: string[]
  }
  stock_impact: {
    bias: string
    magnitude: string
    horizon: string
    confidence: number
    reasons: string[]
  }
  base_case: {
    description: string
    probability_band: string | null
    required_conditions: string[]
  }
  bull_case: {
    description: string
    probability_band: string | null
    required_conditions: string[]
  }
  bear_case: {
    description: string
    probability_band: string | null
    required_conditions: string[]
  }
  what_would_change_view: Array<{
    trigger: string
    description: string
  }>
  confidence: number
  confidence_reasons: string[]
  missing_information: string[]
  supporting_evidence: EvidenceRef[]
  generated_at: string
  engine_version: string
}

export interface EvidenceRef {
  evidence_id: string
  source_type: string
  url: string | null
  description: string
  timestamp: string | null
}

export interface Answer {
  question: string
  answer: string
  confidence: number
  evidence_refs: EvidenceRef[]
  generated_at: string
}

export interface EarningsEvent {
  event_id: string
  symbol: string
  title: string
  released_at: string
  metadata: {
    eps_actual: string | null
    eps_consensus: string | null
    eps_surprise: string | null
    revenue_actual: number | null
    revenue_consensus: number | null
    revenue_surprise: string | null
    guidance_change: string | null
    guidance_details: {
      eps_guidance_low: string | null
      eps_guidance_high: string | null
      revenue_guidance_low: string | null
      revenue_guidance_high: string | null
    } | null
    fiscal_quarter: string | null
    fiscal_year: string | null
  }
}

export interface CompanyEvent {
  event_id: string
  symbol: string | null
  event_type: string
  title: string
  description: string | null
  scheduled_at: string | null
  released_at: string | null
  importance: string
  source: string
  source_url: string | null
  source_id: string | null
  status: string
  timezone: string
  actual: string | null
  forecast: string | null
  previous: string | null
  unit: string | null
  first_seen_at: string
  last_seen_at: string
  created_at: string
  updated_at: string
  content_hash: string
  metadata: Record<string, unknown>
}

export type NewsEvent = CompanyEvent

export type InsiderTransaction = CompanyEvent

export interface LeadershipData {
  symbol: string
  leadership: Record<string, { name: string | null; effective_date: string | null; event_id: string; source: string; source_url: string | null; released_at: string | null }>
}

export interface Filing {
  event_id: string
  title: string
  released_at: string | null
  event_type: string
  metadata: {
    form: string | null
  }
  source_url: string | null
}

export interface QuantSignals extends DataAvailability {
  symbol: string
  quant_score: number | null
  rank: number | null
  universe_size: number | null
  components: Record<string, number>
  calculated_at: string | null
  signals: Record<string, number>
}

export interface QuantCandidate {
  symbol: string
  rank: number
  quant_score: number
  momentum_score: number
  trend_score: number
  liquidity_score: number
  volume_score: number
  volatility_quality_score: number
  price: number
  avg_dollar_volume_20d: number
  components: Record<string, number>
  calculated_at: string
  market_timestamp: string
  source: string
  mode: 'real' | 'demo'
}

export interface MacroEventResponse {
  metadata?: Record<string, unknown>
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

export interface UpcomingEventResponse {
  event_id: string
  title: string
  event_type: string
  scheduled_at: string
  importance: string
  source: string
}

export interface Event {
  event_id: string
  title: string
  event_type: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
}

export interface TermDefinition {
  term: string
  short_definition: string
  long_definition: string | null
  category: string
  reference_type: string
  external_reference_url: string | null
  related_terms: string[]
}

// Phase 11: Watchlists
export interface Watchlist {
  id: string
  name: string
  description: string | null
  sort_order: 'manual' | 'symbol' | 'quant_score' | 'price_change' | 'market_cap'
  is_default: boolean
  created_at: string
  updated_at: string
  item_count: number
  symbols: string[]
}

export interface WatchlistWithItems extends Watchlist {
  items: WatchlistItem[]
}

export interface WatchlistItem {
  symbol: string
  added_at: string
  notes: string | null
  sort_index: number
}

export interface WatchlistCreate {
  name: string
  description?: string
  sort_order?: 'manual' | 'symbol' | 'quant_score' | 'price_change' | 'market_cap'
  is_default?: boolean
}

export interface WatchlistUpdate {
  name?: string
  description?: string
  sort_order?: 'manual' | 'symbol' | 'quant_score' | 'price_change' | 'market_cap'
  is_default?: boolean
}

export interface WatchlistItemCreate {
  symbol: string
  notes?: string
}

export interface WatchlistItemUpdate {
  notes?: string
  sort_index?: number
}

// Phase 11: Calendar
export interface CalendarExportRequest {
  format: 'ics'
  event_types?: string[]
  symbols?: string[]
  from_date?: string
  to_date?: string
  importance?: string[]
}

export interface CalendarExportResponse {
  format: 'ics'
  content: string
  filename: string
  event_count: number
}

// Phase 11: Alerts
export interface Alert {
  id: string
  user_id: string | null
  name: string
  description: string | null
  alert_type: string
  symbols: string[]
  condition: string
  threshold: number | null
  threshold_secondary: number | null
  severity: 'info' | 'warning' | 'critical'
  channels: ('in_app' | 'email' | 'webhook')[]
  is_active: boolean
  cooldown_minutes: number
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
  last_triggered: string | null
  trigger_count: number
}

export interface AlertCreate {
  name: string
  description?: string
  alert_type: string
  symbols: string[]
  condition: string
  threshold: number | null
  threshold_secondary?: number
  severity?: 'info' | 'warning' | 'critical'
  channels?: ('in_app' | 'email' | 'webhook')[]
  is_active?: boolean
  cooldown_minutes?: number
  metadata?: Record<string, unknown>
}

export interface AlertUpdate {
  name?: string
  description?: string
  symbols?: string[]
  condition?: string
  threshold?: number | null
  threshold_secondary?: number | null
  severity?: 'info' | 'warning' | 'critical'
  channels?: ('in_app' | 'email' | 'webhook')[]
  is_active?: boolean
  cooldown_minutes?: number
  metadata?: Record<string, unknown>
}

export interface AlertTrigger {
  id: string
  alert_id: string
  symbol: string
  alert_type: string
  message: string
  value: number | null
  threshold: number | null
  severity: string
  triggered_at: string
  acknowledged: boolean
  acknowledged_at: string | null
  metadata: Record<string, unknown>
}

export interface AlertTestRequest {
  alert_id: string
}

export interface AlertTestResponse {
  status?: string
  would_trigger: boolean | null
  symbols_checked: string[]
  current_values: Record<string, unknown>
  message?: string
}

export interface AlertEvaluationResponse extends AlertTestResponse {
  triggers: AlertTrigger[]
  delivery: 'in_app_history_only'
}
