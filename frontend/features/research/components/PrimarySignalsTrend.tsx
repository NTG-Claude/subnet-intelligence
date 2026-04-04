'use client'

import { useEffect, useMemo, useState } from 'react'

import { CompareSeriesData, fetchCompareTimeseries } from '@/lib/api'
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type TrendPoint = {
  computed_at: string
  score: number
  quality: number | null
  opportunity: number | null
  risk: number | null
  confidence: number | null
}

const SERIES = [
  { key: 'score', label: 'Score', color: '#7db8ff', strokeWidth: 2.6 },
  { key: 'quality', label: 'Quality', color: '#58d68d', strokeWidth: 2.2 },
  { key: 'opportunity', label: 'Opportunity', color: '#ffb347', strokeWidth: 2.2 },
  { key: 'risk', label: 'Risk', color: '#ff5ca8', strokeWidth: 2.2 },
  { key: 'confidence', label: 'Confidence', color: '#bd93ff', strokeWidth: 2.2 },
] as const

type SeriesKey = (typeof SERIES)[number]['key']
type TimeframeId = '24h' | '7d' | '30d' | 'all'

const TIMEFRAMES: { id: TimeframeId; label: string; days: number | null }[] = [
  { id: '24h', label: '24H', days: 1 },
  { id: '7d', label: '7D', days: 7 },
  { id: '30d', label: '30D', days: 30 },
  { id: 'all', label: 'All', days: null },
]

const DETAIL_TREND_CACHE_KEY = 'detail-compare-timeseries-v1'
const DETAIL_TREND_CACHE_TTL_MS = 5 * 60 * 1000

let cachedTimeseries: CompareSeriesData | null = null
let cachedTimeseriesFetchedAt = 0
let cachedTimeseriesPromise: Promise<CompareSeriesData> | null = null

function hasFreshCachedTimeseries(now = Date.now()): boolean {
  return Boolean(cachedTimeseries && now - cachedTimeseriesFetchedAt < DETAIL_TREND_CACHE_TTL_MS)
}

function rememberTimeseries(data: CompareSeriesData, now = Date.now()) {
  cachedTimeseries = data
  cachedTimeseriesFetchedAt = now

  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(
      DETAIL_TREND_CACHE_KEY,
      JSON.stringify({
        fetchedAt: now,
        data,
      }),
    )
  }
}

function readStoredTimeseries(): CompareSeriesData | null {
  if (typeof window === 'undefined') return null

  const raw = window.sessionStorage.getItem(DETAIL_TREND_CACHE_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { fetchedAt?: number; data?: CompareSeriesData }
    if (!parsed.fetchedAt || !parsed.data) return null
    if (Date.now() - parsed.fetchedAt >= DETAIL_TREND_CACHE_TTL_MS) return null

    cachedTimeseries = parsed.data
    cachedTimeseriesFetchedAt = parsed.fetchedAt
    return parsed.data
  } catch {
    return null
  }
}

function getCachedTimeseries(): CompareSeriesData | null {
  if (hasFreshCachedTimeseries()) {
    return cachedTimeseries
  }

  return readStoredTimeseries()
}

async function loadCachedTimeseries(days: number): Promise<CompareSeriesData> {
  const existing = getCachedTimeseries()
  if (existing) return existing

  if (!cachedTimeseriesPromise) {
    cachedTimeseriesPromise = fetchCompareTimeseries(days)
      .then((data) => {
        rememberTimeseries(data)
        return data
      })
      .finally(() => {
        cachedTimeseriesPromise = null
      })
  }

  return cachedTimeseriesPromise
}

function filterPointsByTimeframe(points: TrendPoint[], timeframe: TimeframeId): TrendPoint[] {
  if (timeframe === 'all' || points.length < 2) return points

  const timeframeConfig = TIMEFRAMES.find((item) => item.id === timeframe)
  if (!timeframeConfig?.days) return points

  const newest = new Date(points[points.length - 1].computed_at).getTime()
  const cutoff = newest - timeframeConfig.days * 24 * 60 * 60 * 1000

  return points.filter((point) => new Date(point.computed_at).getTime() >= cutoff)
}

function toTrendPoints(data: CompareSeriesData | null, netuid: number): TrendPoint[] {
  if (!data) return []

  return data.runs
    .map((run) => {
      const point = run.subnets.find((item) => item.netuid === netuid)
      if (!point) return null

      return {
        computed_at: run.computed_at,
        score: point.score,
        quality: point.fundamental_quality,
        opportunity: point.mispricing_signal,
        risk: point.fragility_risk,
        confidence: point.signal_confidence,
      }
    })
    .filter((point): point is TrendPoint => Boolean(point))
}

function formatAxisDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(value))
}

function formatTooltipDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function TrendTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ dataKey?: string; value?: number; color?: string; name?: string }>
  label?: string
}) {
  if (!active || !payload?.length || !label) return null

  return (
    <div className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(7,14,20,0.96)] p-3 shadow-2xl">
      <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{formatTooltipDate(label)}</div>
      <div className="mt-2 space-y-1.5">
        {payload.map((entry) =>
          typeof entry.value === 'number' ? (
            <div key={entry.dataKey} className="flex items-center justify-between gap-4 text-sm">
              <div className="flex items-center gap-2 text-[color:var(--text-secondary)]">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span>{entry.name}</span>
              </div>
              <span className="font-medium text-[color:var(--text-primary)]">{entry.value.toFixed(1)}</span>
            </div>
          ) : null,
        )}
      </div>
    </div>
  )
}

export default function PrimarySignalsTrend({ netuid }: { netuid: number }) {
  const [points, setPoints] = useState<TrendPoint[]>(() => toTrendPoints(getCachedTimeseries(), netuid))
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>(points.length ? 'ready' : 'loading')
  const [activeSeries, setActiveSeries] = useState<Record<SeriesKey, boolean>>({
    score: true,
    quality: true,
    opportunity: true,
    risk: true,
    confidence: true,
  })
  const [timeframe, setTimeframe] = useState<TimeframeId>('30d')

  useEffect(() => {
    const existing = getCachedTimeseries()
    if (existing) {
      setPoints(toTrendPoints(existing, netuid))
      setStatus('ready')
      return
    }

    let cancelled = false

    async function loadTrend() {
      try {
        const data = await loadCachedTimeseries(120)
        if (!cancelled) {
          setPoints(toTrendPoints(data, netuid))
          setStatus('ready')
        }
      } catch {
        if (!cancelled) {
          setStatus('unavailable')
        }
      }
    }

    void loadTrend()

    return () => {
      cancelled = true
    }
  }, [netuid])

  const visibleSeries = SERIES.filter((series) => activeSeries[series.key])
  const filteredPoints = useMemo(() => filterPointsByTimeframe(points, timeframe), [points, timeframe])

  function toggleSeries(key: SeriesKey) {
    setActiveSeries((current) => {
      const next = { ...current, [key]: !current[key] }
      return next
    })
  }

  if (status === 'loading') {
    return (
      <div className="mt-5 rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.42)] px-6 py-8 text-center">
        <div className="text-sm font-medium text-[color:var(--text-primary)]">Loading signal history</div>
        <div className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
          The trend chart loads after the core subnet research so the page opens faster.
        </div>
      </div>
    )
  }

  if (points.length < 2) {
    return (
      <div className="mt-5 rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.42)] px-6 py-8 text-center">
        <div className="text-sm font-medium text-[color:var(--text-primary)]">
          {status === 'unavailable' ? 'Signal history is currently unavailable' : 'Signal history is not available yet'}
        </div>
        <div className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
          This chart appears once there are enough completed runs to show how score, quality, opportunity, risk, and confidence are changing over time.
        </div>
      </div>
    )
  }

  return (
    <div className="mt-5 rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.52)] p-4 sm:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="eyebrow">Visible lines</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SERIES.map((series) => {
              const isActive = activeSeries[series.key]
              return (
                <button
                  key={series.key}
                  type="button"
                  onClick={() => toggleSeries(series.key)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium uppercase tracking-[0.14em] transition ${
                    isActive
                      ? 'border-[color:var(--border-strong)] bg-[color:rgba(18,30,42,0.92)] text-[color:var(--text-primary)]'
                      : 'border-[color:var(--border-subtle)] bg-transparent text-[color:var(--text-tertiary)]'
                  }`}
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: series.color, opacity: isActive ? 1 : 0.45 }} />
                  <span>{series.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="lg:text-right">
          <div className="eyebrow">Timeframe</div>
          <div className="mt-3 flex flex-wrap gap-2 lg:justify-end">
            {TIMEFRAMES.map((option) => {
              const isActive = timeframe === option.id
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setTimeframe(option.id)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium uppercase tracking-[0.14em] transition ${
                    isActive
                      ? 'border-[color:var(--border-strong)] bg-[color:rgba(18,30,42,0.92)] text-[color:var(--text-primary)]'
                      : 'border-[color:var(--border-subtle)] bg-transparent text-[color:var(--text-tertiary)]'
                  }`}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {visibleSeries.length ? (
        <div className="mt-4 h-[280px] sm:h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filteredPoints} margin={{ top: 10, right: 8, left: 0, bottom: 6 }}>
              <CartesianGrid stroke="rgba(138, 163, 184, 0.14)" vertical={false} />
              <XAxis
                dataKey="computed_at"
                tickFormatter={formatAxisDate}
                minTickGap={28}
                stroke="rgba(138, 163, 184, 0.45)"
                tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
              />
              <YAxis
                domain={[0, 100]}
                width={40}
                stroke="rgba(138, 163, 184, 0.45)"
                tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
              />
              <Tooltip content={<TrendTooltip />} />
              {visibleSeries.map((series) => (
                <Line
                  key={series.key}
                  type="monotone"
                  dataKey={series.key}
                  name={series.label}
                  stroke={series.color}
                  strokeWidth={series.strokeWidth}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-4 rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.42)] px-6 py-8 text-center">
          <div className="text-sm font-medium text-[color:var(--text-primary)]">No lines are currently visible</div>
          <div className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
            Turn one or more signals back on to compare how this subnet has been moving across runs.
          </div>
        </div>
      )}
    </div>
  )
}
