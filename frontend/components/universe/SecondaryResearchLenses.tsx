import Link from 'next/link'

import { SubnetSummary } from '@/lib/api'
import { UNIVERSE_LENSES, applyUniverseLens, toUniverseRow } from '@/lib/view-models/research'
import { HintBadge, StatusBadge } from '@/components/shared/research-ui'

export default function SecondaryResearchLenses({ subnets }: { subnets: SubnetSummary[] }) {
  const boards = UNIVERSE_LENSES.filter((lens) => lens.id !== 'all')
    .slice(0, 4)
    .map((lens) => ({
      ...lens,
      rows: applyUniverseLens(subnets, lens.id).slice(0, 3).map(toUniverseRow),
    }))

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {boards.map((board) => (
        <section key={board.id} className="rounded-3xl border border-white/10 bg-[#11161c] p-5">
          <div className="space-y-1">
            <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Research lens</div>
            <h3 className="text-lg font-semibold text-stone-50">{board.title}</h3>
            <p className="text-sm leading-6 text-stone-400">{board.description}</p>
          </div>

          <div className="mt-4 space-y-3">
            {board.rows.map((row) => (
              <Link key={row.id} href={row.href} className="block rounded-2xl border border-white/10 bg-stone-950 p-4 transition-colors hover:bg-[#161c23]">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
                  <StatusBadge tone="neutral">{row.label}</StatusBadge>
                </div>

                <div className="mt-3 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-base font-semibold text-stone-100">{row.name}</div>
                    <p className="mt-1 text-sm leading-6 text-stone-400">{row.decisionLine}</p>
                  </div>
                  <div className="min-w-[120px] text-right">
                    <div className="text-xs uppercase tracking-[0.2em] text-stone-500">Trust</div>
                    <div className="mt-1 text-sm text-stone-100">{row.trustLabel}</div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {(row.opportunityNotes.length ? row.opportunityNotes : row.uncertaintyNotes).slice(0, 2).map((item) => (
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
