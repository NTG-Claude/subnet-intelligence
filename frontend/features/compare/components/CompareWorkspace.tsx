'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import PageHeader from '@/components/ui/PageHeader'
import { CompareSeriesData } from '@/lib/api'
import { cn } from '@/lib/formatting'

type MetricKey = 'score' | 'fundamental_quality' | 'mispricing_signal' | 'fragility_risk' | 'signal_confidence'

type ChartSeries = {
  key: string
  name: string
  color: string
  latestValue: number | null
  highlighted: boolean
}

type ChartPoint = {
  computed_at: string
  label: string
  [key: string]: string | number | null
}

type HoverSnapshotItem = {
  key: string
  name: string
  color: string
  value: number
  highlighted: boolean
}

const HIGHLIGHT_COLORS = ['#ff4fa3', '#67e26f', '#ffb347', '#74b3ff', '#c084fc', '#44d9e6']

const METRIC_CONFIG: Array<{
  key: MetricKey
  title: string
  subtitle: string
  lowerIsBetter?: boolean
  formatter: (value: number) => string
}> = [
  {
    key: 'score',
    title: 'Score',
    subtitle: 'Total score across runs. This is the cleanest view of broad relative positioning over time.',
    formatter: (value) => value.toFixed(1),
  },
  {
    key: 'fundamental_quality',
    title: 'Quality',
    subtitle: 'How fundamental quality evolves run by run across the subnet universe.',
    formatter: (value) => value.toFixed(1),
  },
  {
    key: 'mispricing_signal',
    title: 'Opportunity',
    subtitle: 'Where the model still sees residual upside and mispricing potential after each run.',
    formatter: (value) => value.toFixed(1),
  },
  {
    key: 'fragility_risk',
    title: 'Risk',
    subtitle: 'Lower is better. This shows which subnets remain more resilient under stress across runs.',
    lowerIsBetter: true,
    formatter: (value) => value.toFixed(1),
  },
  {
    key: 'signal_confidence',
    title: 'Confidence',
    subtitle: 'How clean, trustworthy, and decision-usable the underlying read looks over time.',
    formatter: (value) => value.toFixed(1),
  },
]

function formatAxisLabel(value: string): string {
  const date = new Date(value)
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(date)
}

function formatTooltipLabel(value: string): string {
  const date = new Date(value)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function subnetLabel(name: string | null | undefined, netuid: number): string {
  return name?.trim() || `SN${netuid}`
}

function buildChartModel(data: CompareSeriesData, metric: MetricKey) {
  const latestRun = data.runs[data.runs.length - 1]
  const latestSorted = [...(latestRun?.subnets ?? [])]
    .filter((item) => item[metric] != null)
    .sort((left, right) => {
      const leftValue = left[metric] as number
      const rightValue = right[metric] as number
      if (metric === 'fragility_risk') return leftValue - rightValue
      return rightValue - leftValue
    })

  const highlightIds = new Set(latestSorted.slice(0, 6).map((item) => item.netuid))
  const colorById = new Map<number, string>()
  latestSorted.slice(0, 6).forEach((item, index) => {
    colorById.set(item.netuid, HIGHLIGHT_COLORS[index] ?? HIGHLIGHT_COLORS[HIGHLIGHT_COLORS.length - 1])
  })

  const chartData: ChartPoint[] = data.runs.map((run) => {
    const point: ChartPoint = {
      computed_at: run.computed_at,
      label: formatAxisLabel(run.computed_at),
    }
    run.subnets.forEach((subnet) => {
      point[`sn_${subnet.netuid}`] = subnet[metric]
    })
    return point
  })

  const series: ChartSeries[] = (latestRun?.subnets ?? [])
    .filter((subnet) => subnet[metric] != null)
    .map((subnet) => ({
      key: `sn_${subnet.netuid}`,
      name: subnetLabel(subnet.name, subnet.netuid),
      color: colorById.get(subnet.netuid) ?? '#58708a',
      latestValue: subnet[metric],
      highlighted: highlightIds.has(subnet.netuid),
    }))
    .sort((left, right) => {
      if (left.highlighted !== right.highlighted) return Number(right.highlighted) - Number(left.highlighted)
      return (right.latestValue ?? -Infinity) - (left.latestValue ?? -Infinity)
    })

  return {
    chartData,
    series,
    highlights: series.filter((item) => item.highlighted),
  }
}

function CustomTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean
  payload?: Array<{ dataKey?: string; value?: number; color?: string; name?: string }>
  label?: string
  formatter: (value: number) => string
}) {
  if (!active || !payload?.length || !label) return null

  const items = payload
    .filter((item): item is { dataKey?: string; value: number; color?: string; name?: string } => typeof item.value === 'number')
    .sort((left, right) => right.value - left.value)

  return (
    <div className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(7,14,20,0.94)] p-3 shadow-2xl">
      <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{formatTooltipLabel(label)}</div>
      <div className="mt-2 text-sm text-[color:var(--text-secondary)]">
        {items.length} subnets in this run. Full hovered snapshot is shown below the chart.
      </div>
    </div>
  )
}

function HoverSnapshot({
  title,
  computedAt,
  items,
  formatter,
  lowerIsBetter,
}: {
  title: string
  computedAt: string | null
  items: HoverSnapshotItem[]
  formatter: (value: number) => string
  lowerIsBetter?: boolean
}) {
  if (!computedAt || !items.length) return null

  return (
    <div className="mt-4 rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.6)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow">{title}</div>
          <div className="mt-1 text-sm text-[color:var(--text-secondary)]">{formatTooltipLabel(computedAt)}</div>
        </div>
        <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">
          {lowerIsBetter ? 'Lowest to highest risk' : 'Highest to lowest'}
        </div>
      </div>
      <div className="mt-3 grid max-h-[260px] gap-2 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item, index) => (
          <div
            key={`${item.key}-${computedAt}`}
            className={cn(
              'flex items-center justify-between rounded-[var(--radius-sm)] border border-[color:var(--border-subtle)] px-3 py-2.5',
              item.highlighted && 'bg-[color:rgba(16,29,41,0.88)]',
            )}
          >
            <div className="flex min-w-0 items-center gap-2">
              <span className="font-mono text-[11px] text-[color:var(--text-tertiary)]">#{index + 1}</span>
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="truncate text-sm text-[color:var(--text-primary)]">{item.name}</span>
            </div>
            <span className="shrink-0 font-mono text-sm text-[color:var(--text-secondary)]">{formatter(item.value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MetricRunChart({
  title,
  subtitle,
  chartData,
  series,
  highlights,
  formatter,
  lowerIsBetter,
  dense,
}: {
  title: string
  subtitle: string
  chartData: ChartPoint[]
  series: ChartSeries[]
  highlights: ChartSeries[]
  formatter: (value: number) => string
  lowerIsBetter?: boolean
  dense?: boolean
}) {
  const [hoveredRun, setHoveredRun] = useState<string | null>(chartData[chartData.length - 1]?.computed_at ?? null)

  const hoverItems = useMemo(() => {
    const point = chartData.find((item) => item.computed_at === hoveredRun) ?? chartData[chartData.length - 1]
    if (!point) return []
    return series
      .map((item) => {
        const value = point[item.key]
        return typeof value === 'number'
          ? {
              key: item.key,
              name: item.name,
              color: item.color,
              value,
              highlighted: item.highlighted,
            }
          : null
      })
      .filter((item): item is HoverSnapshotItem => Boolean(item))
      .sort((left, right) => (lowerIsBetter ? left.value - right.value : right.value - left.value))
      .slice(0, 18)
  }, [chartData, hoveredRun, lowerIsBetter, series])

  return (
    <section className="surface-panel p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="section-title">{title}</div>
          <p className="mt-1 text-sm text-[color:var(--text-secondary)]">{subtitle}</p>
        </div>
        {lowerIsBetter ? (
          <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Lower is better</div>
        ) : null}
      </div>

      <div className={cn('h-[360px] w-full', dense && 'h-[300px]')}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 16, right: 18, left: 0, bottom: 0 }}
            onMouseMove={(state) => {
              const nextLabel = typeof state?.activeLabel === 'string' ? state.activeLabel : null
              if (nextLabel) setHoveredRun(nextLabel)
            }}
          >
            <CartesianGrid stroke="rgba(138, 163, 184, 0.14)" vertical={false} />
            <XAxis
              dataKey="computed_at"
              tickFormatter={formatAxisLabel}
              minTickGap={28}
              stroke="rgba(138, 163, 184, 0.45)"
              tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
            />
            <YAxis
              stroke="rgba(138, 163, 184, 0.45)"
              tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
              tickFormatter={formatter}
              width={52}
            />
            <Tooltip content={<CustomTooltip formatter={formatter} />} />
            {series.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name}
                stroke={line.color}
                strokeWidth={line.highlighted ? 2.2 : 0.9}
                strokeOpacity={line.highlighted ? 0.95 : 0.18}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <HoverSnapshot
        title="Hovered Run Snapshot"
        computedAt={hoveredRun}
        items={hoverItems}
        formatter={formatter}
        lowerIsBetter={lowerIsBetter}
      />

      <div className="mt-4">
        <div className="eyebrow">Latest Leaders</div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {highlights.map((item) => (
            <div key={item.key} className="flex items-center justify-between rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.6)] px-3 py-2.5">
              <div className="flex min-w-0 items-center gap-2">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="truncate text-sm text-[color:var(--text-primary)]">{item.name}</span>
              </div>
              <span className="shrink-0 font-mono text-sm text-[color:var(--text-secondary)]">
                {item.latestValue != null ? formatter(item.latestValue) : 'n/a'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default function CompareWorkspace({ data }: { data: CompareSeriesData }) {
  const [days, setDays] = useState<'14' | '30' | '90'>('30')

  const slicedData = useMemo(() => {
    if (days === '90') return data
    const cutoff = days === '14' ? 14 : 30
    const since = Date.now() - cutoff * 24 * 60 * 60 * 1000
    return {
      ...data,
      runs: data.runs.filter((run) => new Date(run.computed_at).getTime() >= since),
    }
  }, [data, days])

  const metricCharts = useMemo(
    () =>
      METRIC_CONFIG.map((metric) => ({
        ...metric,
        ...buildChartModel(slicedData, metric.key),
      })),
    [slicedData],
  )

  return (
    <div className="space-y-6 pb-16">
      <PageHeader
        title="Compare runs"
        subtitle="Five clean run-over-run charts show how the subnet universe evolves across score, quality, opportunity, risk, and confidence."
        actions={
          <>
            <Link href="/" className="button-secondary">
              Back to discover
            </Link>
            <div className="flex items-center gap-2 rounded-full border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.7)] p-1">
              {(['14', '30', '90'] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setDays(option)}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-xs font-medium tracking-[0.16em] text-[color:var(--text-secondary)] transition-colors',
                    days === option && 'bg-[color:var(--surface-2)] text-[color:var(--text-primary)]',
                  )}
                >
                  {option}D
                </button>
              ))}
            </div>
          </>
        }
        stats={[
          { label: 'Runs', value: String(slicedData.runs.length) },
          { label: 'Subnets', value: String(slicedData.total_subnets) },
        ]}
      />

      {!slicedData.runs.length ? (
        <section className="surface-panel p-10 text-center text-sm text-[color:var(--text-secondary)]">
          No run history available yet for the selected window.
        </section>
      ) : (
        <>
          <MetricRunChart {...metricCharts[0]} />
          <div className="grid gap-6 xl:grid-cols-2">
            {metricCharts.slice(1).map((chart) => {
              const { key, ...chartProps } = chart
              return <MetricRunChart key={key} {...chartProps} dense />
            })}
          </div>
        </>
      )}
    </div>
  )
}
