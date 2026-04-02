import Link from 'next/link'

import { SubnetSummary } from '@/lib/api'
import { toUniverseRow } from '@/lib/view-models/research'
import { HintBadge, StatusBadge, cn } from '@/components/shared/research-ui'

interface Props {
  top: SubnetSummary[]
  bottom: SubnetSummary[]
}

function SnapshotColumn({
  title,
  subtitle,
  rows,
  accent,
}: {
  title: string
  subtitle: string
  rows: SubnetSummary[]
  accent: 'sky' | 'amber'
}) {
  const accentClasses =
    accent === 'sky'
      ? 'border-sky-500/20 bg-sky-500/[0.05]'
      : 'border-amber-500/20 bg-amber-500/[0.05]'

  return (
    <section className={cn('rounded-[1.75rem] border p-4 sm:p-5', accentClasses)}>
      <div className="space-y-1">
        <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{title}</div>
        <p className="text-sm leading-6 text-stone-400">{subtitle}</p>
      </div>

      <div className="mt-4 space-y-3">
        {rows.slice(0, 5).map((subnet) => {
          const row = toUniverseRow(subnet)
          return (
            <Link
              key={subnet.netuid}
              href={row.href}
              className="block rounded-2xl border border-white/10 bg-stone-950/90 p-4 transition-colors hover:bg-[#151c24]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-lg font-semibold text-stone-50">{row.rankLabel}</div>
                    <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
                  </div>
                  <div className="mt-2 text-base font-medium text-stone-200">{row.name}</div>
                  <p className="mt-1 text-sm leading-6 text-stone-400">{row.decisionLine}</p>
                </div>
                <div className="min-w-[132px] text-right">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-stone-500">Model label</div>
                  <div className="mt-1 inline-flex justify-end">
                    <StatusBadge tone={row.modelLabelTone}>{row.modelLabel}</StatusBadge>
                  </div>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {(row.opportunityNotes.length ? row.opportunityNotes : row.uncertaintyNotes).slice(0, 2).map((item) => (
                  <HintBadge key={item.label} label={item.label} tone={item.tone} />
                ))}
              </div>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

export default function RankingSnapshot({ top, bottom }: Props) {
  if (!top.length && !bottom.length) return null

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.95fr)]">
      <SnapshotColumn
        title="Overall ranking"
        subtitle="This is the default answer. Start with the highest-ranked names, then drill into why they earned that position."
        rows={top}
        accent="sky"
      />
      <SnapshotColumn
        title="Needs caution"
        subtitle="Bottom-ranked names or unstable reads that deserve skepticism before deeper work."
        rows={bottom}
        accent="amber"
      />
    </div>
  )
}
