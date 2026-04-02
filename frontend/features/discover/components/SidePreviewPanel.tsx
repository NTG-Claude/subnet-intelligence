import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import { UniverseRowViewModel } from '@/lib/view-models/research'

type MetricRankMap = {
  strength: number
  upside: number
  risk: number
  evidence: number
  total: number
}

export default function SidePreviewPanel({
  row,
  metricRanks,
  selected,
  onToggleCompare,
}: {
  row: UniverseRowViewModel | null
  metricRanks: MetricRankMap | null
  selected: boolean
  onToggleCompare: (id: number) => void
}) {
  return (
    <aside className="surface-panel sticky top-24 hidden h-fit p-5 xl:block">
      {row ? (
        <div className="space-y-5">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
              <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</h2>
            </div>
          </div>

          {metricRanks ? (
            <div className="space-y-3">
              <div className="eyebrow">How It Stacks Up</div>
              <div className="grid gap-3">
                <div className="surface-subtle p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">Strength</div>
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                      #{metricRanks.strength} of {metricRanks.total}
                    </div>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.metricReasons.strength}</p>
                </div>

                <div className="surface-subtle p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">Upside Gap</div>
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                      #{metricRanks.upside} of {metricRanks.total}
                    </div>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.metricReasons.upside}</p>
                </div>

                <div className="surface-subtle p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">Risk</div>
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                      #{metricRanks.risk} of {metricRanks.total} by lowest risk
                    </div>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.metricReasons.risk}</p>
                </div>

                <div className="surface-subtle p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">Evidence Quality</div>
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-tertiary)]">
                      #{metricRanks.evidence} of {metricRanks.total}
                    </div>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.metricReasons.evidence}</p>
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-3">
            <button type="button" onClick={() => onToggleCompare(row.id)} className="button-secondary">
              {selected ? 'Remove from compare' : 'Add to compare'}
            </button>
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
