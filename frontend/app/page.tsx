import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchLatestRun, fetchMarketOverview, fetchSubnets } from '@/lib/api'

const MARKET_OVERVIEW_DAYS = 365

function DiscoverUnavailable({ message }: { message: string }) {
  return (
    <div className="space-y-6 pb-20">
      <section className="surface-panel p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="eyebrow">Service status</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">
            Discover data is temporarily unavailable
          </h1>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-secondary)]">{message}</p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-tertiary)]">
            The homepage intentionally avoids rendering misleading empty leaderboard data when the backend cannot be reached.
          </p>
        </div>
      </section>
    </div>
  )
}

export default async function HomePage() {
  const [subnetsResult, latestResult, marketResult] = await Promise.allSettled([
    fetchSubnets(200),
    fetchLatestRun(),
    fetchMarketOverview(MARKET_OVERVIEW_DAYS),
  ])

  if (subnetsResult.status !== 'fulfilled') {
    return (
      <DiscoverUnavailable message="The frontend could not reach the subnet API during the initial page render. Once the API connection is restored, the ranked subnet list and market summary will load normally." />
    )
  }

  const { subnets } = subnetsResult.value
  const latest =
    latestResult.status === 'fulfilled'
      ? latestResult.value
      : { last_score_run: null, subnet_count: subnets.length }
  const market =
    marketResult.status === 'fulfilled'
      ? marketResult.value
      : {
          current_market_cap_tao: 0,
          current_market_cap_usd: null,
          tao_price_usd: null,
          change_pct_vs_previous_run: null,
          current_subnet_count: subnets.length,
          points: [],
        }

  const currentMarketCap = subnets.reduce((sum, subnet) => sum + (subnet.market_cap_tao ?? 0), 0)
  const marketWithFallback =
    market.current_market_cap_tao > 0 || market.points.length
      ? market
      : {
          current_market_cap_tao: currentMarketCap,
          current_market_cap_usd:
            market.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
          tao_price_usd: market.tao_price_usd ?? null,
          change_pct_vs_previous_run: null,
          current_subnet_count: latest.subnet_count || subnets.length,
          points: latest.last_score_run
            ? [
                {
                  computed_at: latest.last_score_run,
                  total_market_cap_tao: currentMarketCap,
                  total_market_cap_usd:
                    market.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
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
      initialTimeseries={null}
    />
  )
}
