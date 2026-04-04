import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchLatestRun, fetchMarketOverview, fetchSubnets } from '@/lib/api'

function firstValue(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null
  return value ?? null
}

const MARKET_TIMEFRAME_DAYS = {
  '7d': 7,
  '30d': 30,
  '90d': 90,
  '180d': 180,
  max: 365,
} as const

type MarketTimeframeId = keyof typeof MARKET_TIMEFRAME_DAYS

function parseMarketTimeframe(value: string | null): MarketTimeframeId {
  if (value && value in MARKET_TIMEFRAME_DAYS) {
    return value as MarketTimeframeId
  }
  return 'max'
}

interface HomePageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {}
  const marketTimeframe = parseMarketTimeframe(firstValue(resolvedSearchParams.tf))
  const [{ subnets }, latest, market] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
    fetchMarketOverview(MARKET_TIMEFRAME_DAYS[marketTimeframe]).catch(() => ({
      current_market_cap_tao: 0,
      current_market_cap_usd: null,
      tao_price_usd: null,
      change_pct_vs_previous_run: null,
      current_subnet_count: 0,
      points: [],
    })),
  ])

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
      initialMarketTimeframe={marketTimeframe}
      initialSearch={firstValue(resolvedSearchParams.q) ?? ''}
      initialSort={firstValue(resolvedSearchParams.sort) ?? 'rank'}
      initialDirection={firstValue(resolvedSearchParams.dir) ?? 'asc'}
      initialCompareIds={firstValue(resolvedSearchParams.ids)}
    />
  )
}
