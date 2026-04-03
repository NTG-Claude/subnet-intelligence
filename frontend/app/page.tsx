import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchLatestRun, fetchMarketOverview, fetchSubnets } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const [{ subnets }, latest, market] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
    fetchMarketOverview(90).catch(() => ({
      current_market_cap_tao: 0,
      change_pct_vs_previous_run: null,
      current_subnet_count: 0,
      points: [],
    })),
  ])

  const scored = subnets.filter((subnet) => subnet.primary_outputs)
  const lowConfidenceCount = scored.filter((subnet) => (subnet.primary_outputs?.signal_confidence ?? 0) < 50).length
  const awaitingRunCount = subnets.length - scored.length
  const currentMarketCap = subnets.reduce((sum, subnet) => sum + (subnet.market_cap_tao ?? 0), 0)
  const marketWithFallback =
    market.current_market_cap_tao > 0 || market.points.length
      ? market
      : {
          current_market_cap_tao: currentMarketCap,
          change_pct_vs_previous_run: null,
          current_subnet_count: latest.subnet_count || subnets.length,
          points: latest.last_score_run
            ? [
                {
                  computed_at: latest.last_score_run,
                  total_market_cap_tao: currentMarketCap,
                  subnet_count: latest.subnet_count || subnets.length,
                },
              ]
            : [],
        }

  return (
    <DiscoverWorkspace
      subnets={subnets}
      lastRun={latest.last_score_run}
      market={marketWithFallback}
      trackedUniverse={latest.subnet_count || subnets.length}
      awaitingRunCount={awaitingRunCount}
      lowConfidenceCount={lowConfidenceCount}
    />
  )
}
