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
    )

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

  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
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

  // Search symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
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

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Interpretation
  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, { params: { as_of: asOf } })
  }

  // Answer
  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
  }

  // Earnings
  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  // Events
  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, {
      params: { event_types: eventTypes?.join(','), limit }
    })
  }

  // News
  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, { params: { limit, from_date, to_date } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Leadership
  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  // Filings
  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Quant signals
  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  // Quant scanner
  async getQuantScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, { params: { timeframe, start, end, limit } })
  }

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Interpretation
  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, { params: { as_of: asOf } })
  }

  // Answer
  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
  }

  // Earnings
  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  // Events
  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, { params: { event_types: eventTypes?.join(','), limit } })
  }

  // News
  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, { params: { limit, from_date: fromDate, to_date: toDate } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Leadership
  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  // Filings
  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  // Insiders
  async getInsiders2(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Quant signals
  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  // Quant scanner
  async getQuantScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, { params: { timeframe, start, end, limit } })
  }

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Interpretation
  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, { params: { as_of: asOf } })
  }

  // Answer
  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
  }

  // Earnings
  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  // Events
  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, { params: { event_types: eventTypes?.join(','), limit } })
  }

  // News
  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, { params: { limit, from_date: fromDate, to_date: toDate } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Leadership
  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  // Filings
  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  // Insiders
  async getInsiders2(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Quant signals
  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  // Quant scanner
  async getQuantScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, { params: { timeframe, start, end, limit } })
  }

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Interpretation
  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, { params: { as_of: asOf } })
  }

  // Answer
  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
  }

  // Earnings
  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  // Events
  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, { params: { event_types: eventTypes?.join(','), limit } })
  }

  // News
  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, { params: { limit, from_date: fromDate, to_date: toDate } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Leadership
  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  // Filings
  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  // Insiders
  async getInsiders2(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Quant signals
  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  // Quant scanner
  async getQuantScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, { params: { timeframe, start, end, limit } })
  }

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Interpretation
  async getInterpretation(symbol: string, asOf?: string) {
    return this.get<Interpretation>(`/stocks/${symbol}/interpretation`, { params: { as_of: asOf } })
  }

  // Answer
  async answerQuestion(symbol: string, question: string) {
    return this.post<Answer>(`/stocks/${symbol}/answer`, { question })
  }

  // Earnings
  async getEarnings(symbol: string) {
    return this.get<EarningsEvent[]>(`/stocks/${symbol}/earnings`)
  }

  // Events
  async getEvents(symbol: string, eventTypes?: string[], limit?: number) {
    return this.get<CompanyEvent[]>(`/stocks/${symbol}/events`, { params: { event_types: eventTypes?.join(','), limit } })
  }

  // News
  async getNews(symbol: string, limit?: number, fromDate?: string, toDate?: string) {
    return this.get<NewsEvent[]>(`/stocks/${symbol}/news`, { params: { limit, from_date: fromDate, to_date: toDate } })
  }

  // Insiders
  async getInsiders(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Leadership
  async getLeadership(symbol: string) {
    return this.get<LeadershipData>(`/stocks/${symbol}/leadership`)
  }

  // Filings
  async getFilings(symbol: string, limit?: number) {
    return this.get<Filing[]>(`/stocks/${symbol}/filings`, { params: { limit } })
  }

  // Insiders
  async getInsiders2(symbol: string, limit?: number) {
    return this.get<InsiderTransaction[]>(`/stocks/${symbol}/insiders`, { params: { limit } })
  }

  // Quant signals
  async getQuantSignals(symbol: string) {
    return this.get<QuantSignals>(`/stocks/${symbol}/quant`)
  }

  // Quant scanner
  async getQuantScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }

  // Terms
  async getTermDefinition(term: string) {
    return this.get<TermDefinition>(`/terms/${encodeURIComponent(term)}`)
  }

  async searchTerms(query: string, limit?: number) {
    return this.get<TermDefinition[]>(`/terms/search`, { params: { q: query, limit } })
  }

  // Symbols
  async searchSymbols(query: string, limit?: number) {
    return this.get<SymbolSearchResult[]>('/symbols/search', { params: { q: query, limit } })
  }

  // Market data
  async getMarketOverview() {
    return this.get<MarketOverviewResponse>('/market/overview')
  }

  async getBars(symbol: string, timeframe: string, start?: string, end?: string, limit?: number) {
    return this.get<BarData>(`/market/bars/${symbol}`, { params: { timeframe, start, end, limit } })
  }

  // Scanner
  async getScannerTop(n: number = 20) {
    return this.get<QuantCandidate[]>(`/scanner/top`, { params: { n } })
  }
}

export const api = new ApiClient()