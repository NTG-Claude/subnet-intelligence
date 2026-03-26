const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface SubnetSummary {
  netuid: number
  name: string | null
  score: number
  rank: number | null
  percentile: number | null
  computed_at: string | null
  score_version: string
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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { next: { revalidate: 3600 } })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const fetchSubnets = (limit = 100) =>
  get<{ total: number; subnets: SubnetSummary[] }>(`/api/v1/subnets?limit=${limit}`)

export const fetchSubnet = (netuid: number) =>
  get<SubnetDetail>(`/api/v1/subnets/${netuid}`)

export const fetchLeaderboard = () =>
  get<LeaderboardData>('/api/v1/leaderboard')

export const fetchDistribution = () =>
  get<{ buckets: DistributionBucket[]; total_subnets: number }>('/api/v1/scores/distribution?buckets=10')

export const fetchLatestRun = () =>
  get<{ last_score_run: string | null; subnet_count: number }>('/api/v1/scores/latest')
