const DEV_SERVER_API = 'http://localhost:8000'

type ApiFetchOptions = {
  revalidate?: number
  cache?: RequestCache
}

const DEFAULT_REVALIDATE_SECONDS = 600
const DETAIL_REVALIDATE_SECONDS = 180
const TIMESERIES_REVALIDATE_SECONDS = 300

export interface SubnetSummary {
  netuid: number
  name: string | null
  score: number
  primary_outputs: PrimaryOutputs | null
  rank: number | null
  previous_rank?: number | null
  preview_metric_deltas?: PreviewMetricDeltas | null
  percentile: number | null
  computed_at: string | null
  score_version: string
  alpha_price_tao: number | null
  tao_in_pool: number | null
  market_cap_tao: number | null
  staking_apy: number | null
  investability_status: string | null
  warning_flags: string[]
  /** Deprecated compatibility field. Prefer thesis and V2 explanation data in product UI. */
  label: string | null
  thesis: string | null
  analysis_preview?: AnalysisPreview | null
}

export interface ScoreBreakdown {
  capital_score: number
  activity_score: number
  efficiency_score: number
  health_score: number
  dev_score: number
}

export interface PrimaryOutputs {
  fundamental_quality: number
  mispricing_signal: number
  fragility_risk: number
  signal_confidence: number
}

export interface ResearchSummary {
  setup_status: 'strong_setup' | 'improving_setup' | 'fragile_setup' | 'not_investable'
  setup_read: string
  why_now: string
  main_constraint: string
  break_condition: string
  market_capacity: 'very_low' | 'low' | 'medium' | 'high'
  evidence_strength: 'high' | 'medium' | 'low'
  relative_peer_context: string
}

export interface DriverItem {
  metric: string
  effect: number
  value: number | null
  normalized: number
  category: string
}

export interface ExplanationContributor {
  metric?: string
  name?: string
  category?: string
  value?: number | null
  normalized?: number
  contribution?: number
  signed_contribution?: number
  direction?: string
  short_explanation?: string
  source_block?: string
}

export interface KeyUncertainty {
  name: string
  signed_contribution?: number
  direction?: string
  short_explanation?: string
  source_block?: string
}

export interface ConditioningInfo {
  reliability?: Record<string, number>
  visibility?: Record<string, string[]>
}

export interface ConfidenceRationale extends RationaleBucket {
  evidence_confidence?: number
  thesis_confidence?: number
  data_confidence?: number
  market_confidence?: number
}

export interface AnalysisPreview {
  top_positive_drivers?: ExplanationContributor[]
  top_negative_drags?: ExplanationContributor[]
  key_uncertainties?: KeyUncertainty[]
  conditioning?: ConditioningInfo
  block_scores?: Record<string, number>
}

export interface SubnetAnalysis {
  /** Deprecated compatibility field. Prefer thesis and V2 explanation data in product UI. */
  label?: string
  thesis?: string
  primary_outputs?: PrimaryOutputs
  component_scores?: Record<string, number>
  block_scores?: Record<string, number>
  top_positive_drivers?: ExplanationContributor[]
  top_negative_drags?: ExplanationContributor[]
  top_negative_drivers?: ExplanationContributor[]
  primary_signal_contributors?: Record<string, ExplanationContributor[]>
  key_uncertainties?: KeyUncertainty[]
  why_mispriced?: RationaleBucket
  risk_drivers?: RationaleBucket
  confidence_rationale?: ConfidenceRationale
  quality_rationale?: RationaleBucket
  thesis_breakers?: string[]
  activated_hard_rules?: string[]
  stress_drawdown?: number
  fragility_class?: string
  earned_reflexive_fragile?: Record<string, number>
  debug_metrics?: Record<string, unknown>
  conditioning?: ConditioningInfo
  stress_scenarios?: { name: string; score_after: number; drawdown: number }[]
}

export interface RationaleBucket {
  supports?: DriverItem[]
  headwinds?: DriverItem[]
  fragility?: DriverItem[]
  offsets?: DriverItem[]
}

export interface SubnetDetail {
  netuid: number
  name: string | null
  score: number
  primary_outputs: PrimaryOutputs | null
  rank: number | null
  percentile: number | null
  breakdown?: ScoreBreakdown | null
  history?: { computed_at: string; score: number; rank: number | null }[]
  metadata: {
    netuid: number
    name: string | null
    github_url: string | null
    website: string | null
    first_seen: string | null
    last_updated: string | null
  } | null
  computed_at: string | null
  score_version: string
  alpha_price_tao: number | null
  tao_in_pool: number | null
  market_cap_tao: number | null
  staking_apy: number | null
  score_delta_7d: number | null
  investability_status: string | null
  warning_flags: string[]
  /** Deprecated compatibility field. Prefer thesis and V2 explanation data in product UI. */
  label: string | null
  thesis: string | null
  research_summary?: ResearchSummary | null
  analysis: SubnetAnalysis | null
}

export interface DistributionBucket {
  range_start: number
  range_end: number
  count: number
}

export interface LeaderboardData {
  top: SubnetSummary[]
  bottom: SubnetSummary[]
}

export interface BacktestLabelSummary {
  label: string
  observations: number
  avg_relative_forward_return_vs_tao_30d: number | null
  avg_relative_forward_return_vs_tao_90d: number | null
  avg_drawdown_risk: number | null
  avg_liquidity_deterioration_risk: number | null
  avg_concentration_deterioration_risk: number | null
}

export interface BacktestData {
  observations: number
  targets: string[]
  labels: BacktestLabelSummary[]
  examples: {
    netuid: number
    start_at: string | null
    end_at: string | null
    label: string
    score: number | null
    fundamental_quality: number | null
    mispricing_signal: number | null
    fragility_risk: number | null
    signal_confidence: number | null
    relative_forward_return_vs_tao_30d: number | null
    relative_forward_return_vs_tao_90d: number | null
    drawdown_risk: number | null
    liquidity_deterioration_risk: number | null
    concentration_deterioration_risk: number | null
    legacy_opportunity_gap: number | null
    legacy_stress_robustness: number | null
  }[]
}

export interface CompareSeriesSubnetPoint {
  netuid: number
  name: string | null
  score: number
  fundamental_quality: number | null
  mispricing_signal: number | null
  fragility_risk: number | null
  signal_confidence: number | null
}

export interface CompareSeriesRunPoint {
  computed_at: string
  subnets: CompareSeriesSubnetPoint[]
}

export interface CompareSeriesData {
  runs: CompareSeriesRunPoint[]
  total_subnets: number
}

export interface SubnetSignalHistoryPoint {
  computed_at: string
  score: number
  quality: number | null
  opportunity: number | null
  risk: number | null
  confidence: number | null
}

export interface MetricDeltaValue {
  value: number | null
  has_history: boolean
}

export interface PreviewMetricDeltas {
  strength: Record<string, MetricDeltaValue>
  upside: Record<string, MetricDeltaValue>
  risk: Record<string, MetricDeltaValue>
  evidence: Record<string, MetricDeltaValue>
}

export interface MarketOverviewPoint {
  computed_at: string
  total_market_cap_tao: number
  total_market_cap_usd: number | null
  subnet_count: number
}

export interface MarketOverviewData {
  current_market_cap_tao: number
  current_market_cap_usd: number | null
  tao_price_usd: number | null
  change_pct_vs_previous_run: number | null
  current_subnet_count: number
  points: MarketOverviewPoint[]
}

export interface DiscoverBootstrapData {
  subnets: SubnetSummary[]
  last_score_run: string | null
  subnet_count: number
  market: MarketOverviewData
}

function getServerApiOrigin(): string {
  const apiOrigin = process.env.NEXT_PUBLIC_API_URL || process.env.RAILWAY_API_URL
  if (apiOrigin) return apiOrigin
  if (process.env.NODE_ENV !== 'production') return DEV_SERVER_API

  throw new Error(
    'Missing API origin for server-side frontend fetches. Set RAILWAY_API_URL or NEXT_PUBLIC_API_URL in production.',
  )
}

async function get<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { revalidate = DEFAULT_REVALIDATE_SECONDS, cache } = options
  const init: RequestInit & { next?: { revalidate: number } } = {}
  const baseUrl = typeof window === 'undefined' ? getServerApiOrigin() : ''

  if (cache) {
    init.cache = cache
  }

  if (typeof window === 'undefined') {
    if (cache === 'no-store') {
      init.cache = 'no-store'
    } else {
      init.next = { revalidate }
    }
  }

  const res = await fetch(`${baseUrl}${path}`, init)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const fetchSubnets = (limit = 200) =>
  get<{ total: number; subnets: SubnetSummary[] }>(`/api/v1/subnets?limit=${limit}&preview=compact`, {
    revalidate: DEFAULT_REVALIDATE_SECONDS,
  })

export const fetchSubnet = (netuid: number) =>
  get<SubnetDetail>(`/api/v1/subnets/${netuid}?view=page`, { revalidate: DETAIL_REVALIDATE_SECONDS })

export const fetchLeaderboard = () =>
  get<LeaderboardData>('/api/v1/leaderboard')

export const fetchDistribution = () =>
  get<{ buckets: DistributionBucket[]; total_subnets: number }>('/api/v1/scores/distribution?buckets=10')

export const fetchLatestRun = () =>
  get<{ last_score_run: string | null; subnet_count: number }>('/api/v1/scores/latest', {
    revalidate: TIMESERIES_REVALIDATE_SECONDS,
  })

export const fetchLabelBacktests = (days = 90) =>
  get<BacktestData>(`/api/v1/backtests/labels?days=${days}`)

export const fetchCompareTimeseries = (days = 30) =>
  get<CompareSeriesData>(`/api/v1/compare/timeseries?days=${days}`, {
    revalidate: TIMESERIES_REVALIDATE_SECONDS,
  })

export const fetchSubnetSignalHistory = (netuid: number, days = 120) =>
  get<SubnetSignalHistoryPoint[]>(`/api/v1/subnets/${netuid}/history/signals?days=${days}`, {
    revalidate: TIMESERIES_REVALIDATE_SECONDS,
  })

export const fetchMarketOverview = (days = 90) =>
  get<MarketOverviewData>(`/api/v1/market/overview?days=${days}`, {
    revalidate: DEFAULT_REVALIDATE_SECONDS,
  })

export const fetchDiscoverBootstrap = (limit = 200, marketDays = 365) =>
  get<DiscoverBootstrapData>(`/api/v1/discover/bootstrap?limit=${limit}&market_days=${marketDays}`, {
    revalidate: DEFAULT_REVALIDATE_SECONDS,
  })
