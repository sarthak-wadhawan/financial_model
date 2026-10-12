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

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
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

  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
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
}

export const api = new ApiClient()

// Type definitions for API responses
export interface MarketOverviewResponse {
  market_status: string
  snapshot_time: string
  symbols_tracked: number
  indices: Array<{
    symbol: string
    price: number
    change: number
    change_pct: number
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

export interface BarData {
  symbol: string
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
  name: string
  exchange: string
  type: string
}

export interface StockDetail {
  symbol: string
  name: string
  exchange: string
  price: number
  change: number
  change_pct: number
  volume: number
  market_cap: number
  pe_ratio: number | null
  dividend_yield: number | null
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
    probability_band: string
    required_conditions: string[]
  }
  bull_case: {
    description: string
    probability_band: string
    required_conditions: string[]
  }
  bear_case: {
    description: string
    probability_band: string
    required_conditions: string[]
  }
  what_would_change_view: Array<{
    trigger: string
    description: string
  }>
  confidence: number
  confidence_reasons: string[]
  missing_information: string[]
  supporting_evidence: Array<{
    source_type: string
    url: string
    description: string
    timestamp: string
  }>
}

export interface Answer {
  answer_id: string
  symbol: string
  question: string
  answer: string
  confidence: number
  evidence_refs: string[]
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
  symbol: string
  event_type: string
  title: string
  description: string | null
  scheduled_at: string | null
  released_at: string | null
  importance: string
  source: string
  source_url: string | null
}

export interface NewsEvent {
  document_id: string
  headline: string
  summary: string | null
  publisher: string
  published_at: string
  source_url: string
  source_type: string
}

export interface InsiderTransaction {
  transaction_id: string
  name: string
  role: string
  transaction_type: string
  shares: number
  price: number | null
  transaction_value: number | null
  is_10b5_1: boolean
  holdings_after: number | null
  transaction_date: string
}

export interface LeadershipData {
  ceo: string | null
  cfo: string | null
  [key: string]: string | null
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

export interface QuantSignals {
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
}

export interface MacroEventResponse {
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
  definition: string
  category: string
  source: string
  source_url: string
  related_terms: string[]
}