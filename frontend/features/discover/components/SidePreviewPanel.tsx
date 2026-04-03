import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import { UniverseRowViewModel } from '@/lib/view-models/research'

type MetricDeltaWindow = '1d' | '7d' | '30d'

type MetricDelta = {
  value: number | null
  hasHistory: boolean
}

type MetricDeltaMap = {
  strength: Record<MetricDeltaWindow, MetricDelta>
  upside: Record<MetricDeltaWindow, MetricDelta>
  risk: Record<MetricDeltaWindow, MetricDelta>
  evidence: Record<MetricDeltaWindow, MetricDelta>
}

export default function SidePreviewPanel({
  row,
  metricDeltas,
  metricHistoryStatus,
}: {
  row: UniverseRowViewModel | null
  metricDeltas: MetricDeltaMap | null
  metricHistoryStatus: 'loading' | 'ready' | 'unavailable'
}) {
  return (
    <aside className="surface-panel sticky top-24 hidden h-fit p-4 xl:block">
      {row ? (
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
              <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
            </div>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-[28px] font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</h2>
              </div>

              <div className="min-w-[96px] shrink-0 rounded-[var(--radius-md)] border border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] px-3 py-2 text-right">
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">Score</div>
                <div className="mt-1 font-mono text-[28px] font-semibold leading-none text-[color:var(--text-primary)]">{row.scoreLabel}</div>
              </div>
            </div>
          </div>

          {metricHistoryStatus === 'loading' ? (
            <div className="space-y-2">
              <div className="eyebrow">Metric Change</div>
              <div className="surface-subtle p-3">
                <div className="text-sm text-[color:var(--text-secondary)]">Loading metric history...</div>
              </div>
            </div>
          ) : metricDeltas ? (
            <div className="space-y-2">
              <div className="eyebrow">Metric Change</div>
              <div className="grid gap-2">
                <MetricDeltaSection title="Quality" deltas={metricDeltas.strength} />
                <MetricDeltaSection title="Opportunity" deltas={metricDeltas.upside} />
                <MetricDeltaSection title="Risk" deltas={metricDeltas.risk} invert />
                <MetricDeltaSection title="Confidence" deltas={metricDeltas.evidence} />
              </div>
            </div>
          ) : metricHistoryStatus === 'unavailable' ? (
            <div className="space-y-2">
              <div className="eyebrow">Metric Change</div>
              <div className="surface-subtle p-3">
                <div className="text-sm text-[color:var(--text-secondary)]">Metric history is currently unavailable.</div>
              </div>
            </div>
          ) : null}

          <Link href={row.href} className="button-primary w-full">
            Open research
          </Link>
        </div>
      ) : (
        <div className="flex min-h-[320px] items-center justify-center text-center text-sm leading-6 text-[color:var(--text-secondary)]">
          Hover a subnet row to inspect its current read.
        </div>
      )}
    </aside>
  )
}

function MetricDeltaSection({
  title,
  deltas,
  invert = false,
}: {
  title: string
  deltas: Record<MetricDeltaWindow, MetricDelta>
  invert?: boolean
}) {
  return (
    <div className="surface-subtle p-3">
      <div className="eyebrow">{title}</div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <DeltaPill label="1d" delta={deltas['1d']} invert={invert} />
        <DeltaPill label="7d" delta={deltas['7d']} invert={invert} />
        <DeltaPill label="30d" delta={deltas['30d']} invert={invert} />
      </div>
    </div>
  )
}

function DeltaPill({
  label,
  delta,
  invert = false,
}: {
  label: MetricDeltaWindow
  delta: MetricDelta
  invert?: boolean
}) {
  const display = formatDelta(delta.value)
  const stateClass =
    delta.value == null
      ? 'text-[color:var(--text-tertiary)]'
      : delta.value === 0
        ? 'text-[color:var(--text-primary)]'
        : isPositive(delta.value, invert)
          ? 'text-[color:var(--quality-strong)]'
          : 'text-[color:var(--fragility-strong)]'

  return (
    <div className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.55)] px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">{label}</div>
      <div className={`mt-1 font-mono text-[13px] font-semibold ${stateClass}`}>{display}</div>
    </div>
  )
}

function formatDelta(value: number | null): string {
  if (value == null) return 'n/a'
  if (Object.is(value, -0)) return '0.0'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

function isPositive(value: number, invert: boolean): boolean {
  return invert ? value < 0 : value > 0
}
