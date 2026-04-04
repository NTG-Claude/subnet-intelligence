import { unstable_cache } from 'next/cache'

import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchLatestRun, fetchMarketOverview, fetchSubnets } from '@/lib/api'

const MARKET_OVERVIEW_DAYS = 365
export const dynamic = 'force-dynamic'

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
            The homepage avoids rendering misleading empty leaderboard data when the backend cannot be reached.
          </p>
        </div>
      </section>
    </div>
  )
}

const getHomepagePayload = unstable_cache(
  async () => {
    const [subnetsResult, latestResult, marketResult] = await Promise.allSettled([
      retry(() => fetchSubnets(200)),
      fetchLatestRun(),
      fetchMarketOverview(MARKET_OVERVIEW_DAYS),
    ])

    if (subnetsResult.status !== 'fulfilled') {
      throw new Error('Failed to load discover homepage payload')
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

    return {
      subnets,
      lastRun: latest.last_score_run,
      market: marketWithFallback,
    }
  },
  ['discover-homepage-payload'],
  { revalidate: 300 },
)

export default async function HomePage() {
  let payload
  try {
    payload = await getHomepagePayload()
  } catch {
    return (
      <DiscoverUnavailable message="The frontend could not refresh the discover dataset for this request. Once the backend connection stabilizes, the ranked subnet list and market summary will load normally." />
    )
  }

  return (
    <DiscoverWorkspace
      subnets={payload.subnets}
      lastRun={payload.lastRun}
      market={payload.market}
      initialTimeseries={null}
    />
  )
}
