'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

import CompareWorkspace from '@/features/compare/components/CompareWorkspace'
import { CompareSeriesData, fetchCompareTimeseries } from '@/lib/api'

const MAX_RETRIES = 3
const RETRY_DELAYS_MS = [0, 1200, 2600]

function CompareLoadingState({ attempt }: { attempt: number }) {
  return (
    <div className="space-y-6 pb-16">
      <section className="surface-panel p-10 text-center">
        <div className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-tertiary)]">Compare</div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">Loading run charts</h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[color:var(--text-secondary)]">
          Pulling the latest run history for score, strength, upside, risk, and evidence quality.
          {attempt > 0 ? ` Retrying connection (${attempt + 1}/${MAX_RETRIES})...` : ''}
        </p>
      </section>

      <div className="surface-panel h-[360px] animate-pulse bg-[color:rgba(10,18,26,0.68)]" />
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="surface-panel h-[300px] animate-pulse bg-[color:rgba(10,18,26,0.68)]" />
        <div className="surface-panel h-[300px] animate-pulse bg-[color:rgba(10,18,26,0.68)]" />
        <div className="surface-panel h-[300px] animate-pulse bg-[color:rgba(10,18,26,0.68)]" />
        <div className="surface-panel h-[300px] animate-pulse bg-[color:rgba(10,18,26,0.68)]" />
      </div>
    </div>
  )
}

function CompareErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="surface-panel p-10 text-center">
      <div className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-tertiary)]">Compare</div>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">Charts are temporarily unavailable</h1>
      <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[color:var(--text-secondary)]">
        The compare page could not reach the run-history endpoint just now. The rest of the app is unaffected.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <button type="button" onClick={onRetry} className="button-primary">
          Try again
        </button>
        <Link href="/" className="button-secondary">
          Back to discover
        </Link>
      </div>
    </div>
  )
}

export default function ComparePageClient() {
  const [data, setData] = useState<CompareSeriesData | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    async function load(currentAttempt: number) {
      try {
        setStatus('loading')
        const nextData = await fetchCompareTimeseries(90)
        if (cancelled) return
        setData(nextData)
        setStatus('ready')
      } catch {
        if (cancelled) return
        if (currentAttempt < MAX_RETRIES - 1) {
          const nextAttempt = currentAttempt + 1
          setAttempt(nextAttempt)
          timer = setTimeout(() => {
            void load(nextAttempt)
          }, RETRY_DELAYS_MS[nextAttempt] ?? 1500)
          return
        }
        setStatus('error')
      }
    }

    setData(null)
    setAttempt(0)
    void load(0)

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [reloadKey])

  function retryNow() {
    setReloadKey((current) => current + 1)
  }

  if (status === 'ready' && data) {
    return <CompareWorkspace data={data} />
  }

  if (status === 'error') {
    return <CompareErrorState onRetry={retryNow} />
  }

  return <CompareLoadingState attempt={attempt} />
}
