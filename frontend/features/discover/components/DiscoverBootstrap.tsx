'use client'

import { useEffect, useMemo, useState } from 'react'

import { CompareSeriesData, MarketOverviewData, SubnetSummary } from '@/lib/api'

import DiscoverWorkspace from './DiscoverWorkspace'

const BOOTSTRAP_CACHE_KEY = 'discover-bootstrap-v1'
const BOOTSTRAP_CACHE_TTL_MS = 5 * 60 * 1000

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

async function fetchBootstrap(): Promise<DiscoverBootstrapData> {
  const res = await fetch('/api/discover/bootstrap', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    cache: 'no-store',
  })

  if (!res.ok) {
    throw new Error(`Discover bootstrap request failed with ${res.status}`)
  }

  return res.json()
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
            The homepage keeps its static shell fast, then retries the live bootstrap request at runtime instead of baking
            outage data into the deploy.
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
