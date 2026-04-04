import { fetchLatestRun, fetchMarketOverview, fetchSubnets, MarketOverviewData, SubnetSummary } from '@/lib/api'

const MARKET_OVERVIEW_DAYS = 365
const RETRY_DELAY_MS = 350

type DiscoverBootstrapResponse = {
  subnets: SubnetSummary[]
  lastRun: string | null
  market: MarketOverviewData
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function retryOnce<T>(load: () => Promise<T>): Promise<T> {
  try {
    return await load()
  } catch (error) {
    await delay(RETRY_DELAY_MS)
    return load()
  }
}

function buildMarketFallback({
  subnets,
  lastRun,
  subnetCount,
  market,
}: {
  subnets: SubnetSummary[]
  lastRun: string | null
  subnetCount: number
  market: MarketOverviewData
}): MarketOverviewData {
  const currentMarketCap = subnets.reduce((sum, subnet) => sum + (subnet.market_cap_tao ?? 0), 0)

  if (market.current_market_cap_tao > 0 || market.points.length) {
    return market
  }

  return {
    current_market_cap_tao: currentMarketCap,
    current_market_cap_usd: market.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
    tao_price_usd: market.tao_price_usd ?? null,
    change_pct_vs_previous_run: null,
    current_subnet_count: subnetCount || subnets.length,
    points: lastRun
      ? [
          {
            computed_at: lastRun,
            total_market_cap_tao: currentMarketCap,
            total_market_cap_usd: market.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
            subnet_count: subnetCount || subnets.length,
          },
        ]
      : [],
  }
}

export async function GET() {
  const [subnetsResult, latestResult, marketResult] = await Promise.allSettled([
    retryOnce(() => fetchSubnets(200)),
    retryOnce(() => fetchLatestRun()),
    retryOnce(() => fetchMarketOverview(MARKET_OVERVIEW_DAYS)),
  ])

  if (subnetsResult.status !== 'fulfilled') {
    return Response.json(
      {
        error: 'The discover bootstrap endpoint could not load ranked subnets from the backend.',
      },
      {
        status: 503,
        headers: {
          'Cache-Control': 'no-store',
        },
      },
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

  const payload: DiscoverBootstrapResponse = {
    subnets,
    lastRun: latest.last_score_run,
    market: buildMarketFallback({
      subnets,
      lastRun: latest.last_score_run,
      subnetCount: latest.subnet_count,
      market,
    }),
  }

  return Response.json(payload, {
    headers: {
      'Cache-Control': 's-maxage=300, stale-while-revalidate=600',
    },
  })
}
