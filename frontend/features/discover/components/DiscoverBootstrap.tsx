'use client'

import { useEffect, useMemo, useState } from 'react'

import {
  CompareSeriesData,
  fetchLatestRun,
  fetchMarketOverview,
  fetchSubnets,
  MarketOverviewData,
  SubnetSummary,
} from '@/lib/api'

import DiscoverWorkspace from './DiscoverWorkspace'

const BOOTSTRAP_CACHE_KEY = 'discover-bootstrap-v1'
const BOOTSTRAP_CACHE_TTL_MS = 5 * 60 * 1000
const MARKET_OVERVIEW_DAYS = 365
const RETRY_DELAY_MS = 350

type DiscoverBootstrapData = {
  subnets: SubnetSummary[]
  lastRun: string | null
  market: MarketOverviewData
}

type BootstrapState = {
  status: 'loading' | 'ready' | 'error'
  data: DiscoverBootstrapData | null
  error: string | null
}

let inMemoryBootstrapCache: { fetchedAt: number; data: DiscoverBootstrapData } | null = null

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function hasFreshCache(fetchedAt: number, now = Date.now()) {
  return now - fetchedAt < BOOTSTRAP_CACHE_TTL_MS
}

function rememberBootstrap(data: DiscoverBootstrapData, now = Date.now()) {
  inMemoryBootstrapCache = { fetchedAt: now, data }

  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(
      BOOTSTRAP_CACHE_KEY,
      JSON.stringify({
        fetchedAt: now,
        data,
      }),
    )
  }
}

function readBootstrapCache(): DiscoverBootstrapData | null {
  if (inMemoryBootstrapCache && hasFreshCache(inMemoryBootstrapCache.fetchedAt)) {
    return inMemoryBootstrapCache.data
  }

  if (typeof window === 'undefined') return null

  const raw = window.sessionStorage.getItem(BOOTSTRAP_CACHE_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { fetchedAt?: number; data?: DiscoverBootstrapData }
    if (!parsed.fetchedAt || !parsed.data || !hasFreshCache(parsed.fetchedAt)) {
      return null
    }

    inMemoryBootstrapCache = {
      fetchedAt: parsed.fetchedAt,
      data: parsed.data,
    }

    return parsed.data
  } catch {
    return null
  }
}

async function retryOnce<T>(load: () => Promise<T>): Promise<T> {
  try {
    return await load()
  } catch {
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

async function fetchBootstrap(): Promise<DiscoverBootstrapData> {
  const [subnetsResult, latestResult, marketResult] = await Promise.allSettled([
    retryOnce(() => fetchSubnets(200)),
    retryOnce(() => fetchLatestRun()),
    retryOnce(() => fetchMarketOverview(MARKET_OVERVIEW_DAYS)),
  ])

  if (subnetsResult.status !== 'fulfilled') {
    throw new Error('Discover bootstrap request failed to load ranked subnets')
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

  return {
    subnets,
    lastRun: latest.last_score_run,
    market: buildMarketFallback({
      subnets,
      lastRun: latest.last_score_run,
      subnetCount: latest.subnet_count,
      market,
    }),
  }
}

function LoadingShell() {
  return (
    <div className="space-y-6 pb-28">
      <section className="surface-panel p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="eyebrow">Loading discover data</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">
            Preparing the ranked subnet view
          </h1>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-secondary)]">
            The homepage shell is already rendered. Live market and subnet data are loading in the background.
          </p>
        </div>
      </section>
    </div>
  )
}

function ErrorShell({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="space-y-6 pb-28">
      <section className="surface-panel p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="eyebrow">Service status</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">
            Discover data is temporarily unavailable
          </h1>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-secondary)]">{message}</p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-tertiary)]">
            The homepage keeps its static shell fast, then loads the live discover data at runtime without depending on a
            deploy-time bootstrap route.
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--border-strong)] px-5 text-sm font-medium text-[color:var(--text-primary)] transition-colors hover:bg-[color:rgba(255,255,255,0.04)]"
          >
            Retry loading
          </button>
        </div>
      </section>
    </div>
  )
}

export default function DiscoverBootstrap() {
  const cachedData = useMemo(() => readBootstrapCache(), [])
  const [reloadToken, setReloadToken] = useState(0)
  const [state, setState] = useState<BootstrapState>(
    cachedData
      ? {
          status: 'ready',
          data: cachedData,
          error: null,
        }
      : {
          status: 'loading',
          data: null,
          error: null,
        },
  )

  useEffect(() => {
    let cancelled = false

    if (!cachedData || reloadToken > 0) {
      setState((current) => ({
        status: current.data ? 'ready' : 'loading',
        data: current.data,
        error: null,
      }))
    }

    void fetchBootstrap()
      .then((data) => {
        if (cancelled) return
        rememberBootstrap(data)
        setState({
          status: 'ready',
          data,
          error: null,
        })
      })
      .catch(() => {
        if (cancelled) return
        setState((current) => {
          if (current.data) {
            return {
              status: 'ready',
              data: current.data,
              error: null,
            }
          }

          return {
            status: 'error',
            data: null,
            error:
              'The frontend could not reach the subnet API bootstrap during this visit. Retry once the backend connection recovers.',
          }
        })
      })

    return () => {
      cancelled = true
    }
  }, [cachedData, reloadToken])

  if (state.status === 'loading') {
    return <LoadingShell />
  }

  if (state.status === 'error' || !state.data) {
    return <ErrorShell message={state.error ?? 'The discover bootstrap is currently unavailable.'} onRetry={() => setReloadToken((value) => value + 1)} />
  }

  return (
    <DiscoverWorkspace
      subnets={state.data.subnets}
      lastRun={state.data.lastRun}
      market={state.data.market}
      initialTimeseries={null as CompareSeriesData | null}
    />
  )
}
