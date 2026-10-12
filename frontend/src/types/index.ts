export interface SymbolInfo {
  symbol: string
  name: string
  exchange: string
  asset_type: string
}

export interface DailyBar {
  symbol: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface MarketSnapshot {
  symbol: string
  latest_price: number
  daily_change: number
  daily_change_pct: number
  timestamp: string
}

export interface FeatureRow {
  symbol: string
  as_of: string
  close: number
  returns_1d: number
  returns_21d: number
  returns_63d: number
  returns_126d: number
  sma_20: number
  sma_50: number
  sma_200: number
  distance_sma_20: number
  distance_sma_50: number
  distance_sma_200: number
  realized_vol_20d: number
  avg_dollar_volume_20d: number
  relative_volume: number
  max_drawdown_20d: number
  rel_returns_21d: number
  rel_returns_63d: number
  rel_returns_126d: number
  avg_dollar_volume_20d: number
}

export interface QuantScore {
  symbol: string
  quant_score: number
  components: {
    momentum: number
    trend: number
    liquidity: number
    volume: number
    volatility_quality: number
  }
}

export interface EligibilityResult {
  symbol: string
  eligible: boolean
  reasons: string[]
}

export interface EvidenceClaim {
  claim: string
  source_ids: string[]
}

export interface CatalystAnalysis {
  symbol: string
  catalyst_type: string
  catalyst_direction: string
  catalyst_strength: string
  summary: string
  guidance_change: string
  key_positive_claims: any[]
  key_negative_claims: any[]
  risks: any[]
  upcoming_events: any[]
  extraction_confidence: number
}

export interface FinalCandidate {
  symbol: string
  quant_score: number
  components: {
    momentum: number
    trend: number
    liquidity: number
    volume: number
    volatility_quality: number
  }
  price: number
  returns_1d: number
  returns_21d: number
  returns_63d: number
  returns_126d: number
  sma_20: number
  sma_50: number
  sma_200: number
  avg_dollar_volume_20d: number
  relative_volume: number
  realized_vol_20d: number
}

export interface ResearchBrief {
  symbol: string
  quant_score: number
  interpretation: string
  key_risks: string[]
  key_catalysts: string[]
  confidence: number
  generated_at: string
}

export interface RunManifest {
  run_id: string
  started_at: string
  completed_at: string
  config_hash: string
  git_commit: string | null
  universe_size: number
  eligible_count: number
  top_n: number
  failures: string[]
}

export interface SourceDocument {
  source_id: string
  symbol: string
  source_type: string
  title: string
  published_at: string
  url: string
  provider: string
  text: string
  retrieval_time: string
  content_hash: string
  metadata: Record<string, any>
}

export interface EvidenceClaim {
  claim: string
  source_ids: string[]
}

export interface QuantCandidate {
  symbol: string
  quant_score: number
  momentum_score: number
  trend_score: number
  liquidity_score: number
  volume_score: number
  volatility_quality_score: number
  price: number
  as_of: string
}

export interface MarketOverviewResponse {
  timestamp: string
  symbols_tracked: number
  quant_scanner_status: string
  market_data_status: string
}

export interface BarData {
  symbol: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface SymbolSearchResult {
  symbol: string
  name: string
  exchange: string
  asset_type: string
}

export interface NewsEvent {
  document_id: string
  symbol: string | null
  headline: string
  body: string
  summary: string | null
  publisher: string
  published_at: string
  retrieved_at: string
  source_url: string
  source_type: string
  author: string | null
  provider_id: string
  content_hash: string
  metadata: Record<string, any>
  dedup_key: string | null
  related_documents: string[]
  sec_filing_id: string | null
  exhibit_number: string | null
}

export interface EarningsEvent {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: {
    eps_actual?: string
    eps_consensus?: string
    eps_surprise?: string
    revenue_actual?: string
    revenue_consensus?: string
    revenue_surprise?: string
    guidance_change?: string
    guidance_details?: {
      eps_guidance_low?: string
      eps_guidance_high?: string
      revenue_guidance_low?: string
      revenue_guidance_high?: string
      guidance_change?: string
      period?: string
    }
  }
}

export interface CompanyEvent {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: Record<string, any>
}

export interface InsiderTransaction {
  transaction_id: string
  symbol: string
  name: string
  role: string
  transaction_date: string
  filing_date: string
  transaction_type: string
  shares: number
  price: number | null
  transaction_value: number | null
  holdings_after: number | null
  is_10b5_1: boolean
  classification: string
  source: string
  source_url: string
}

export interface LeadershipData {
  ceo?: string
  cfo?: string
  [key: string]: string | undefined
}

export interface Filing {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: {
    form?: string
    accession_number?: string
    filing_date?: string
    period_end?: string
    items?: string[]
  }
}

export interface QuantSignals {
  symbol: string
  signals: Record<string, number>
  as_of: string
}

export interface QuantCandidate {
  symbol: string
  quant_score: number
  momentum_score: number
  trend_score: number
  liquidity_score: number
  volume_score: number
  volatility_quality_score: number
  price: number
  as_of: string
}

export interface MarketOverviewResponse {
  timestamp: string
  symbols_tracked: number
  quant_scanner_status: string
  market_data_status: string
}

export interface UpcomingEventResponse {
  event_id: string
  title: string
  event_type: string
  scheduled_at: string
  importance: string
  source: string
}

export interface EarningsEvent {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: {
    eps_actual?: string
    eps_consensus?: string
    eps_surprise?: string
    revenue_actual?: string
    revenue_consensus?: string
    revenue_surprise?: string
    guidance_change?: string
    guidance_details?: {
      eps_guidance_low?: string
      eps_guidance_high?: string
      revenue_guidance_low?: string
      revenue_guidance_high?: string
      guidance_change?: string
      period?: string
    }
  }
}

export interface CompanyEvent {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: Record<string, any>
}

export interface InsiderTransaction {
  transaction_id: string
  symbol: string
  name: string
  role: string
  transaction_date: string
  filing_date: string
  transaction_type: string
  shares: number
  price: number | null
  transaction_value: number | null
  holdings_after: number | null
  is_10b5_1: boolean
  classification: string
  source: string
  source_url: string
}

export interface LeadershipData {
  ceo?: string
  cfo?: string
  [key: string]: string | undefined
}

export interface Filing {
  event_id: string
  symbol: string
  title: string
  description: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string
  source_id: string
  metadata: {
    form?: string
    accession_number?: string
    filing_date?: string
    period_end?: string
    items?: string[]
  }
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

export interface CompanyEventResponse {
  event_id: string
  symbol: string
  title: string
  event_type: string
  scheduled_at: string | null
  released_at: string | null
  importance: string
  status: string
  source: string
  source_url: string | null
  metadata: Record<string, any>
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

export interface Interpretation {
  interpretation_id: string
  symbol: string
  as_of: string
  headline: string
  what_happened: string
  what_it_means: string
  why_it_matters: string
  company_impact: CompanyImpact
  stock_impact: StockImpact
  base_case: Scenario
  bull_case: Scenario
  bear_case: Scenario
  what_would_change_view: ViewChangeTrigger[]
  confidence: number
  confidence_reasons: string[]
  missing_information: string[]
  supporting_evidence: EvidenceRef[]
  generated_at: string
  engine_version: string
}

export interface CompanyImpact {
  direction: string
  magnitude: string
  horizon: string
  reasons: string[]
  evidence_refs: any[]
  confidence: number
}

export interface StockImpact {
  bias: string
  magnitude: string
  horizon: string
  reasons: string[]
  evidence_refs: any[]
  confidence: number
}

export interface Scenario {
  scenario_type: string
  description: string
  required_conditions: string[]
  evidence_refs: any[]
  probability_band?: string
}

export interface ViewChangeTrigger {
  trigger: string
  description: string
  evidence_refs: any[]
}

export interface EvidenceRef {
  evidence_id: string
  source_type: string
  description: string
  url: string | null
  timestamp: string | null
}

export interface Answer {
  question: string
  answer: string
  evidence_refs: any[]
  confidence: number
  generated_at: string
}

export interface AnswerRequest {
  symbol: string
  question: string
  context?: Record<string, any>
}

export interface TermDefinition {
  term: string
  short_definition: string
  long_definition?: string
  external_reference_url?: string
  reference_type: string
  category: string
  related_terms: string[]
}

export interface ManagementStatement {
  statement_id: string
  symbol: string
  speaker: string
  speaker_role: string | null
  statement: string
  statement_type: string
  source_document_id: string
  source_url: string
  published_at: string
  event_date: string | null
  retrieved_at: string
  evidence_span: {
    start: number
    end: number
    text: string
  } | null
  extraction_method: string
  confidence: number
  source_type: string
  provider_id: string
}

export interface EvidenceClaim {
  claim_id: string
  symbol: string
  claim: string
  category: string
  claim_type: string
  speaker: string | null
  speaker_role: string | null
  source_document_id: string
  source_url: string
  published_at: string
  event_date: string | null
  evidence_span: {
    start: number
    end: number
    text: string
  } | null
  extraction_method: string
  confidence: number
  verification_status: string
  source_type: string
  provider_id: string
  derivation?: string
}

export interface NewsDocument {
  document_id: string
  symbol: string | null
  headline: string
  body: string
  summary: string | null
  publisher: string
  published_at: string
  retrieved_at: string
  source_url: string
  source_type: string
  author: string | null
  provider_id: string
  content_hash: string
  metadata: Record<string, any>
  dedup_key: string | null
  related_documents: string[]
  sec_filing_id: string | null
  exhibit_number: string | null
}

export interface ManagementStatement {
  statement_id: string
  symbol: string
  speaker: string
  speaker_role: string | null
  statement: string
  statement_type: string
  source_document_id: string
  source_url: string
  published_at: string
  event_date: string | null
  retrieved_at: string
  evidence_span: {
    start: number
    end: number
    text: string
  } | null
  extraction_method: string
  confidence: number
  source_type: string
  provider_id: string
}

export interface EvidenceSpan {
  start: number
  end: number
  text: string
}

export interface DeduplicationResult {
  is_duplicate: boolean
  canonical_document_id: string | null
  match_type: string | null
  similarity_score: number | null
}

export interface TermDefinition {
  term: string
  short_definition: string
  long_definition?: string
  external_reference_url?: string
  reference_type: string
  category: string
  related_terms: string[]
}

export interface TermDefinitionService {
  get_definition(term: string): Promise<TermDefinition | undefined>
  search_terms(query: string): Promise<TermDefinition[]>
  get_all_terms(): string[]
  get_terms_by_category(category: string): TermDefinition[]
}

export type EventType = 
  | 'macro'
  | 'earnings'
  | 'earnings_result'
  | 'earnings_guidance'
  | 'earnings_reaction'
  | 'dividend'
  | 'stock_split'
  | 'merger_acquisition'
  | 'spinoff'
  | 'corporate_action'
  | 'leadership'
  | 'insider'
  | 'sec_filing'
  | 'regulatory'
  | 'investor_event'
  | 'product_announcement'
  | 'news'
  | 'other'

export type EventStatus = 'scheduled' | 'released' | 'updated' | 'cancelled' | 'unknown'
export type EventImportance = 'low' | 'medium' | 'high' | 'critical'
export type NewsSourceType = 'sec_exhibit' | 'company_ir' | 'news_rss' | 'structured_provider'
export type StatementType = 'guidance' | 'demand' | 'margins' | 'costs' | 'capital_spending' | 'competition' | 'product' | 'regulation' | 'supply' | 'pricing' | 'strategy' | 'risks' | 'macro_conditions' | 'other'
export type ExtractionMethod = 'deterministic' | 'llm'
export type ClaimType = 'fact' | 'attributed_statement' | 'deterministic_derivation' | 'ai_extraction'
export type VerificationStatus = 'verified' | 'pending' | 'failed'
export type ImpactDirection = 'positive' | 'negative' | 'mixed' | 'neutral' | 'unknown'
export type ImpactMagnitude = 'low' | 'medium' | 'high' | 'unknown'
export type TimeHorizon = 'immediate' | 'short_term' | 'medium_term' | 'long_term' | 'unknown'
export type StockBias = 'bullish' | 'bearish' | 'mixed' | 'neutral' | 'unknown'
export type ScenarioType = 'base' | 'bull' | 'bear'
export type ExtractionMethod = 'deterministic' | 'llm'
export type ClaimType = 'fact' | 'attributed_statement' | 'deterministic_derivation' | 'ai_extraction'
export type VerificationStatus = 'verified' | 'pending' | 'failed'
export type ImpactDirection = 'positive' | 'negative' | 'mixed' | 'neutral' | 'unknown'
export type ImpactMagnitude = 'low' | 'medium' | 'high' | 'unknown'
export type TimeHorizon = 'immediate' | 'short_term' | 'medium_term' | 'long_term' | 'unknown'
export type StockBias = 'bullish' | 'bearish' | 'mixed' | 'neutral' | 'unknown'
export type ScenarioType = 'base' | 'bull' | 'bear'
export type ExtractionMethod = 'deterministic' | 'llm'
export type ClaimType = 'fact' | 'attributed_statement' | 'deterministic_derivation' | 'ai_extraction'
export type VerificationStatus = 'verified' | 'pending' | 'failed'