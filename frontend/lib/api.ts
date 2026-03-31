const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface SubnetSummary {
  netuid: number
  name: string | null
  score: number
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
}

export interface ScoreBreakdown {
  capital_score: number
  activity_score: number
  efficiency_score: number
  health_score: number
  dev_score: number
}

export interface SubnetDetail {
  netuid: number
  name: string | null
  score: number
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
  analysis: {
    label?: string
    thesis?: string
    component_scores?: Record<string, number>
    top_positive_drivers?: { metric: string; effect: number; value: number | null; normalized: number; category: string }[]
    top_negative_drivers?: { metric: string; effect: number; value: number | null; normalized: number; category: string }[]
    activated_hard_rules?: string[]
    stress_drawdown?: number
    fragility_class?: string
    earned_reflexive_fragile?: Record<string, number>
    stress_scenarios?: { name: string; score_after: number; drawdown: number }[]
  } | null
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
  avg_future_score_change: number | null
  avg_future_return_proxy: number | null
  avg_future_slippage_deterioration: number | null
  avg_future_concentration_increase: number | null
}

export interface BacktestData {
  observations: number
  labels: BacktestLabelSummary[]
  examples: {
    netuid: number
    start_at: string | null
    end_at: string | null
    label: string
    score: number | null
    future_score_change: number | null
    future_return_proxy: number | null
    future_slippage_deterioration: number | null
    future_concentration_increase: number | null
    opportunity_gap: number | null
    stress_robustness: number | null
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
