'use client'

import { useEffect, useState } from 'react'

import {
  fetchLatestRun,
  fetchMarketOverview,
  fetchSubnets,
  MarketOverviewData,
  SubnetSummary,
} from '@/lib/api'

import DiscoverWorkspace from './DiscoverWorkspace'

const MARKET_OVERVIEW_DAYS = 365
const BOOTSTRAP_CACHE_KEY = 'discover-bootstrap-v1'
const BOOTSTRAP_CACHE_TTL_MS = 5 * 60 * 1000

type DiscoverInitialPayload = {
  subnets: SubnetSummary[]
  lastRun: string | null
  market: MarketOverviewData
}

let cachedPayload: DiscoverInitialPayload | null = null
let cachedPayloadFetchedAt = 0
let cachedPayloadPromise: Promise<DiscoverInitialPayload> | null = null

function hasFreshCachedPayload(now = Date.now()) {
  return Boolean(cachedPayload && now - cachedPayloadFetchedAt < BOOTSTRAP_CACHE_TTL_MS)
}

function rememberPayload(payload: DiscoverInitialPayload, now = Date.now()) {
  cachedPayload = payload
  cachedPayloadFetchedAt = now

  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(
      BOOTSTRAP_CACHE_KEY,
      JSON.stringify({
        fetchedAt: now,
        payload,
      }),
    )
  }
}

function readStoredPayload(): DiscoverInitialPayload | null {
  if (typeof window === 'undefined') return null

  const raw = window.sessionStorage.getItem(BOOTSTRAP_CACHE_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { fetchedAt?: number; payload?: DiscoverInitialPayload }
    if (!parsed.fetchedAt || !parsed.payload) return null
    if (Date.now() - parsed.fetchedAt >= BOOTSTRAP_CACHE_TTL_MS) return null

    cachedPayload = parsed.payload
    cachedPayloadFetchedAt = parsed.fetchedAt
    return parsed.payload
  } catch {
    return null
  }
}

function getCachedPayload(): DiscoverInitialPayload | null {
  if (hasFreshCachedPayload()) return cachedPayload
  return readStoredPayload()
}

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

function buildMarketFallback({
  subnets,
  lastRun,
  subnetCount,
  market,
}: {
  subnets: SubnetSummary[]
  lastRun: string | null
  subnetCount: number
  market: Awaited<ReturnType<typeof fetchMarketOverview>> | null
}): MarketOverviewData {
  const currentMarketCap = subnets.reduce((sum, subnet) => sum + (subnet.market_cap_tao ?? 0), 0)

  if (market && (market.current_market_cap_tao > 0 || market.points.length > 0)) {
    return market
  }

  return {
    current_market_cap_tao: currentMarketCap,
    current_market_cap_usd:
      market?.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
    tao_price_usd: market?.tao_price_usd ?? null,
    change_pct_vs_previous_run: null,
    current_subnet_count: subnetCount || subnets.length,
    points: lastRun
      ? [
          {
            computed_at: lastRun,
            total_market_cap_tao: currentMarketCap,
            total_market_cap_usd:
              market?.tao_price_usd != null ? currentMarketCap * market.tao_price_usd : null,
            subnet_count: subnetCount || subnets.length,
          },
        ]
      : [],
  }
}

async function loadDiscoverPayload(): Promise<DiscoverInitialPayload> {
  const existing = getCachedPayload()
  if (existing) return existing

  if (!cachedPayloadPromise) {
    cachedPayloadPromise = (async () => {
      const { subnets } = await retry(() => fetchSubnets(200))
      const [latestResult, marketResult] = await Promise.allSettled([
        fetchLatestRun(),
        fetchMarketOverview(MARKET_OVERVIEW_DAYS),
      ])

      const lastRun = latestResult.status === 'fulfilled' ? latestResult.value.last_score_run : null
      const subnetCount =
        latestResult.status === 'fulfilled' ? latestResult.value.subnet_count || subnets.length : subnets.length
      const market = buildMarketFallback({
        subnets,
        lastRun,
        subnetCount,
        market: marketResult.status === 'fulfilled' ? marketResult.value : null,
      })

      const payload = { subnets, lastRun, market }
      rememberPayload(payload)
      return payload
    })().finally(() => {
      cachedPayloadPromise = null
    })
  }

  return cachedPayloadPromise
}

function DiscoverLoadingSkeleton() {
  return (
    <div className="space-y-6 pb-20">
      <section className="surface-panel overflow-hidden">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,1fr)]">
          <div className="space-y-4 p-6 sm:p-8">
            <div className="h-3 w-36 rounded-full bg-[color:rgba(255,255,255,0.08)]" />
            <div className="h-14 w-64 rounded-2xl bg-[color:rgba(255,255,255,0.08)]" />
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="h-28 rounded-3xl bg-[color:rgba(255,255,255,0.06)]" />
              <div className="h-28 rounded-3xl bg-[color:rgba(255,255,255,0.06)]" />
            </div>
          </div>
          <div className="p-6 sm:p-8">
            <div className="h-full min-h-[220px] rounded-[28px] border border-dashed border-[color:rgba(255,255,255,0.08)] bg-[color:rgba(6,12,18,0.42)]" />
          </div>
        </div>
      </section>

      <section className="surface-panel p-6 sm:p-8">
        <div className="space-y-4">
          <div className="h-3 w-24 rounded-full bg-[color:rgba(255,255,255,0.08)]" />
          <div className="h-14 rounded-2xl bg-[color:rgba(255,255,255,0.06)]" />
          <div className="grid gap-4 lg:grid-cols-4">
            <div className="h-40 rounded-3xl bg-[color:rgba(255,255,255,0.05)]" />
            <div className="h-40 rounded-3xl bg-[color:rgba(255,255,255,0.05)]" />
            <div className="h-40 rounded-3xl bg-[color:rgba(255,255,255,0.05)]" />
            <div className="h-40 rounded-3xl bg-[color:rgba(255,255,255,0.05)]" />
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="surface-panel overflow-hidden">
          <div className="border-b border-[color:var(--border-subtle)] px-6 py-5">
            <div className="h-8 w-48 rounded-full bg-[color:rgba(255,255,255,0.08)]" />
            <div className="mt-3 h-5 w-80 max-w-full rounded-full bg-[color:rgba(255,255,255,0.06)]" />
          </div>
          <div className="space-y-3 p-4">
            <div className="h-24 rounded-2xl bg-[color:rgba(255,255,255,0.05)]" />
            <div className="h-24 rounded-2xl bg-[color:rgba(255,255,255,0.05)]" />
            <div className="h-24 rounded-2xl bg-[color:rgba(255,255,255,0.05)]" />
          </div>
        </div>
        <div className="surface-panel min-h-[320px] rounded-[32px] bg-[color:rgba(8,16,23,0.58)]" />
      </section>
    </div>
  )
}

function DiscoverUnavailable({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="space-y-6 pb-20">
      <section className="surface-panel p-6 sm:p-8">
        <div className="max-w-3xl">
          <div className="eyebrow">Service status</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">
            Discover data is temporarily unavailable
          </h1>
          <p className="mt-4 text-base leading-7 text-[color:var(--text-secondary)]">
            The homepage shell loaded, but the live subnet data could not be refreshed during this visit.
          </p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-tertiary)]">
            This usually recovers on retry once the backend connection stabilizes.
          </p>
          <button type="button" className="button-secondary mt-6" onClick={onRetry}>
            Retry loading
          </button>
        </div>
      </section>
    </div>
  )
}

export default function DiscoverPageBootstrap({
  initialPayload,
}: {
  initialPayload: DiscoverInitialPayload | null
}) {
  const [payload, setPayload] = useState<DiscoverInitialPayload | null>(() => initialPayload ?? getCachedPayload())
  const [reloadKey, setReloadKey] = useState(0)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>(() =>
    initialPayload || getCachedPayload() ? 'ready' : 'loading',
  )

  useEffect(() => {
    if (initialPayload) {
      rememberPayload(initialPayload)
      setPayload(initialPayload)
      setStatus('ready')
      return
    }

    let cancelled = false

    setStatus('loading')
    loadDiscoverPayload()
      .then((nextPayload) => {
        if (cancelled) return
        setPayload(nextPayload)
        setStatus('ready')
      })
      .catch(() => {
        if (cancelled) return
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [initialPayload, reloadKey])

  if (status === 'ready' && payload) {
    return (
      <DiscoverWorkspace
        subnets={payload.subnets}
        lastRun={payload.lastRun}
        market={payload.market}
      />
    )
  }

  if (status === 'error') {
    return <DiscoverUnavailable onRetry={() => setReloadKey((value) => value + 1)} />
  }

  return <DiscoverLoadingSkeleton />
}
