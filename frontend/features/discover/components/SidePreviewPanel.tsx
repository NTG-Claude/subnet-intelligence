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
    <aside className="surface-panel sticky top-24 hidden h-fit p-5 xl:block">
      {row ? (
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
              <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
            </div>
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</h2>
              </div>

              <div className="min-w-[100px] shrink-0 rounded-[var(--radius-md)] border border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] px-3 py-2.5 text-right">
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">Score</div>
                <div className="mt-1.5 font-mono text-xl font-semibold text-[color:var(--text-primary)]">{row.scoreLabel}</div>
              </div>
            </div>
          </div>

          {metricHistoryStatus === 'loading' ? (
            <div className="space-y-3">
              <div className="eyebrow">Metric Change</div>
              <div className="surface-subtle p-4">
                <div className="text-sm text-[color:var(--text-secondary)]">Loading metric history...</div>
              </div>
            </div>
          ) : metricDeltas ? (
            <div className="space-y-2">
              <div className="eyebrow">Metric Change</div>
              <div className="grid gap-2">
                <div className="surface-subtle p-3">
                  <div className="eyebrow">Quality</div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <DeltaPill label="1d" delta={metricDeltas.strength['1d']} />
                    <DeltaPill label="7d" delta={metricDeltas.strength['7d']} />
                    <DeltaPill label="30d" delta={metricDeltas.strength['30d']} />
                  </div>
                </div>

                <div className="surface-subtle p-3">
                  <div className="eyebrow">Opportunity</div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <DeltaPill label="1d" delta={metricDeltas.upside['1d']} />
                    <DeltaPill label="7d" delta={metricDeltas.upside['7d']} />
                    <DeltaPill label="30d" delta={metricDeltas.upside['30d']} />
                  </div>
                </div>

                <div className="surface-subtle p-3">
                  <div className="eyebrow">Risk</div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <DeltaPill label="1d" delta={metricDeltas.risk['1d']} invert />
                    <DeltaPill label="7d" delta={metricDeltas.risk['7d']} invert />
                    <DeltaPill label="30d" delta={metricDeltas.risk['30d']} invert />
                  </div>
                </div>

                <div className="surface-subtle p-3">
                  <div className="eyebrow">Confidence</div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <DeltaPill label="1d" delta={metricDeltas.evidence['1d']} />
                    <DeltaPill label="7d" delta={metricDeltas.evidence['7d']} />
                    <DeltaPill label="30d" delta={metricDeltas.evidence['30d']} />
                  </div>
                </div>
              </div>
            </div>
          ) : metricHistoryStatus === 'unavailable' ? (
            <div className="space-y-3">
              <div className="eyebrow">Metric Change</div>
              <div className="surface-subtle p-4">
                <div className="text-sm text-[color:var(--text-secondary)]">Metric history is currently unavailable.</div>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-3">
            <Link href={row.href} className="button-primary">
              Open research
            </Link>
          </div>
        </div>
      ) : (
        <div className="flex min-h-[420px] items-center justify-center text-center text-sm leading-6 text-[color:var(--text-secondary)]">
          Hover a subnet row to inspect why it ranks here and what is driving it.
        </div>
      )}
    </aside>
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
    <div className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.55)] px-3 py-1.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">{label}</div>
      <div className={`mt-1.5 font-mono text-sm font-semibold ${stateClass}`}>{display}</div>
      <div className="mt-0.5 text-[11px] text-[color:var(--text-tertiary)]">{delta.hasHistory ? 'vs then' : 'no data'}</div>
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
