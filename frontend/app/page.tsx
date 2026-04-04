import DiscoverPageBootstrap from '@/features/discover/components/DiscoverPageBootstrap'
import { fetchLatestRun, fetchMarketOverview, fetchSubnets } from '@/lib/api'

const MARKET_OVERVIEW_DAYS = 365

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function retry<T>(task: () => Promise<T>, attempts = 2, waitMs = 250): Promise<T> {
  let lastError: unknown

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await task()
    } catch (error) {
      lastError = error
      if (attempt === attempts - 1) break
      await delay(waitMs)
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Failed to load discover data')
}

export default async function HomePage() {
  const [subnetsResult, latestResult, marketResult] = await Promise.allSettled([
    retry(() => fetchSubnets(200)),
    fetchLatestRun(),
    fetchMarketOverview(MARKET_OVERVIEW_DAYS),
  ])

  if (subnetsResult.status !== 'fulfilled') {
    return <DiscoverPageBootstrap initialPayload={null} />
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
    <DiscoverPageBootstrap
      initialPayload={{
        subnets,
        lastRun: latest.last_score_run,
        market: marketWithFallback,
      }}
    />
  )
}
