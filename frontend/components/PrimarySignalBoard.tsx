import Link from 'next/link'

import { SubnetSummary } from '@/lib/api'
import { UNIVERSE_LENSES, applyUniverseLens, toUniverseRow } from '@/lib/view-models/research'
import { HintBadge, StatusBadge } from '@/components/shared/research-ui'

export default function PrimarySignalBoard({ subnets }: { subnets: SubnetSummary[] }) {
  const boards = UNIVERSE_LENSES.filter((lens) => lens.id !== 'all')
    .slice(0, 4)
    .map((lens) => ({
      ...lens,
      rows: applyUniverseLens(subnets, lens.id).slice(0, 3).map(toUniverseRow),
    }))

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {boards.map((board) => (
        <section key={board.id} className="rounded-3xl border border-white/10 bg-white/[0.035] p-5">
          <div className="mb-4 space-y-1">
            <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Research View</div>
            <h3 className="text-lg font-semibold text-stone-50">{board.title}</h3>
            <p className="text-sm leading-6 text-stone-400">{board.description}</p>
          </div>
          <div className="space-y-3">
            {board.rows.map((row) => (
              <Link key={row.id} href={row.href} className="block rounded-2xl border border-white/10 bg-black/20 p-4 transition-colors hover:bg-white/[0.06]">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
                  <StatusBadge tone="neutral">{row.label}</StatusBadge>
                </div>
                <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-base font-semibold text-stone-100">{row.name}</div>
                    <p className="mt-1 text-sm leading-6 text-stone-400">{row.decisionLine}</p>
                  </div>
                  <div className="grid min-w-[180px] grid-cols-2 gap-2 text-right text-xs text-stone-400">
                    {row.signals.map((signal) => (
                      <div key={signal.key}>
                        <div>{signal.shortLabel}</div>
                        <div className="font-semibold text-stone-100">{signal.value?.toFixed(0) ?? 'n/a'}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(row.positives.length ? row.positives : row.warnings).slice(0, 2).map((item) => (
                    <HintBadge key={item.label} label={item.label} tone={item.tone} />
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
