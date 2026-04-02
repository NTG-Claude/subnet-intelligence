import Link from 'next/link'

import TrustBadge from '@/components/ui/TrustBadge'
import StatusChip from '@/components/ui/StatusChip'
import { UniverseRowViewModel } from '@/lib/view-models/research'

export default function SidePreviewPanel({
  row,
  selected,
  onToggleCompare,
}: {
  row: UniverseRowViewModel | null
  selected: boolean
  onToggleCompare: (id: number) => void
}) {
  return (
    <aside className="surface-panel sticky top-24 hidden h-fit p-5 2xl:block">
      {row ? (
        <div className="space-y-5">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
              <StatusChip tone={row.modelLabelTone}>{row.modelLabel}</StatusChip>
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</h2>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
            </div>
          </div>

          <div className="surface-subtle p-4">
            <div className="eyebrow">Thesis</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
          </div>

          <div className="space-y-3">
            <div className="section-title text-base">Top positives</div>
            <div className="space-y-2">
              {row.opportunityNotes.length ? (
                row.opportunityNotes.map((item) => (
                  <div key={item.label} className="surface-subtle p-3 text-sm text-[color:var(--text-secondary)]">
                    {item.label}
                  </div>
                ))
              ) : (
                <div className="surface-subtle p-3 text-sm text-[color:var(--text-tertiary)]">No positive drivers surfaced.</div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="section-title text-base">Top drags</div>
            <div className="space-y-2">
              {row.riskNotes.length ? (
                row.riskNotes.map((item) => (
                  <div key={item.label} className="surface-subtle p-3 text-sm text-[color:var(--text-secondary)]">
                    {item.label}
                  </div>
                ))
              ) : (
                <div className="surface-subtle p-3 text-sm text-[color:var(--text-tertiary)]">No major drags surfaced.</div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="section-title text-base">Trust notes</div>
            <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />
          </div>

          <div className="flex flex-col gap-3">
            <Link href={row.href} className="button-primary">
              Open research
            </Link>
            <button type="button" onClick={() => onToggleCompare(row.id)} className="button-secondary">
              {selected ? 'Remove from compare' : 'Add to compare'}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex min-h-[420px] items-center justify-center text-center text-sm leading-6 text-[color:var(--text-secondary)]">
          Focus a subnet to preview the thesis, trust notes, and quick actions without leaving Discover.
        </div>
      )}
    </aside>
  )
}
