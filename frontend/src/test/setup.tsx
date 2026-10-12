import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock React Router
vi.mock('react-router-dom', () => ({
  ...vi.requireActual('react-router-dom'),
  useParams: () => ({ symbol: 'AAPL' }),
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
  useLocation: () => ({ pathname: '/' }),
}))

// Mock TanStack Query
vi.mock('@tanstack/react-query', () => ({
  ...vi.requireActual('@tanstack/react-query'),
  useQuery: vi.fn(({ queryFn }) => ({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useMutation: vi.fn(),
  QueryClient: vi.fn().mockImplementation(() => ({
    getQueryCache: () => ({ find: vi.fn() }),
    getMutationCache: () => ({ find: vi.fn() }),
  })),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock API
vi.mock('../services/api', () => ({
  api: {
    getInterpretation: vi.fn().mockResolvedValue({
      interpretation_id: 'test-1',
      symbol: 'AAPL',
      as_of: new Date().toISOString(),
      headline: 'Test headline',
      what_happened: 'Test happened',
      what_it_means: 'Test means',
      why_it_matters: 'Test matters',
      company_impact: { direction: 'positive', magnitude: 'high', horizon: 'medium_term', reasons: ['Test reason'], confidence: 0.8 },
      stock_impact: { bias: 'bullish', magnitude: 'medium', horizon: 'short_term', reasons: ['Test reason'], confidence: 0.7 },
      base_case: { description: 'Base case', probability_band: '40-60%', required_conditions: ['Condition 1'] },
      bull_case: { description: 'Bull case', probability_band: '20-30%', required_conditions: ['Condition 1'] },
      bear_case: { description: 'Bear case', probability_band: '15-25%', required_conditions: ['Condition 1'] },
      what_would_change_view: [{ trigger: 'Test trigger', description: 'Test description' }],
      confidence: 0.75,
      confidence_reasons: ['Reason 1'],
      missing_information: ['Missing 1'],
      supporting_evidence: [],
      generated_at: new Date().toISOString(),
      engine_version: '1.0',
    }),
    getEarnings: vi.fn().mockResolvedValue([]),
    getEvents: vi.fn().mockResolvedValue([]),
    getNews: vi.fn().mockResolvedValue([]),
    getInsiders: vi.fn().mockResolvedValue([]),
    getLeadership: vi.fn().mockResolvedValue({ ceo: 'Tim Cook', cfo: 'Luca Maestri' }),
    getFilings: vi.fn().mockResolvedValue([]),
    getQuantSignals: vi.fn().mockResolvedValue({ signals: { momentum: 0.8, trend: 0.7 } }),
    getMarketOverview: vi.fn().mockResolvedValue({ timestamp: new Date().toISOString(), symbols_tracked: 100, quant_scanner_status: 'ready', market_data_status: 'operational' }),
    getQuantScannerTop: vi.fn().mockResolvedValue([{ symbol: 'AAPL', quant_score: 85, rank: 1 }]),
    getTermDefinition: vi.fn().mockResolvedValue({ term: 'EPS', short_definition: 'Earnings Per Share', long_definition: '...', external_reference_url: 'https://sec.gov', reference_type: 'official', category: 'profitability', related_terms: [] }),
    searchTerms: vi.fn().mockResolvedValue([]),
    searchSymbols: vi.fn().mockResolvedValue([{ symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', asset_type: 'stock' }]),
  },
}))

// Mock ThemeContext
vi.mock('../context/ThemeContext', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
  useTheme: () => ({ theme: 'system', resolvedTheme: 'light', setTheme: vi.fn() }),
}))

// Mock Toaster
vi.mock('../components/ui/Toaster', () => ({
  Toaster: () => null,
  ToastProvider: ({ children }: { children: React.ReactNode }) => children,
  useToast: () => ({ addToast: vi.fn(), removeToast: vi.fn() }),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))