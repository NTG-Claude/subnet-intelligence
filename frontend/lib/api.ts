const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface SubnetSummary {
  netuid: number
  name: string | null
  score: number
  primary_outputs: PrimaryOutputs | null
  rank: number | null
  percentile: number | null
  computed_at: string | null
  score_version: string
  alpha_price_tao: number | null
  tao_in_pool: number | null
  market_cap_tao: number | null
  staking_apy: number | null
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
  breakdown: ScoreBreakdown
  history: { computed_at: string; score: number; rank: number | null }[]
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
  label: string | null
  thesis: string | null
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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const fetchSubnets = (limit = 200) =>
  get<{ total: number; subnets: SubnetSummary[] }>(`/api/v1/subnets?limit=${limit}`)

export const fetchSubnet = (netuid: number) =>
  get<SubnetDetail>(`/api/v1/subnets/${netuid}`)

export const fetchLeaderboard = () =>
  get<LeaderboardData>('/api/v1/leaderboard')

export const fetchDistribution = () =>
  get<{ buckets: DistributionBucket[]; total_subnets: number }>('/api/v1/scores/distribution?buckets=10')

export const fetchLatestRun = () =>
  get<{ last_score_run: string | null; subnet_count: number }>('/api/v1/scores/latest')

export const fetchLabelBacktests = (days = 90) =>
  get<BacktestData>(`/api/v1/backtests/labels?days=${days}`)
