import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { UniverseRowViewModel } from '@/lib/view-models/research'

function trustNotes(row: UniverseRowViewModel): string[] {
  const notes = [
    ...row.uncertaintyNotes.map((item) => item.label),
    ...row.statusFlags.map((flag) => flag.label),
  ]

  return notes.filter((item, index) => notes.indexOf(item) === index).slice(0, 4)
}

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
    <aside className="surface-panel sticky top-24 hidden h-fit p-5 xl:block">
      {row ? (
        <div className="space-y-5">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{row.rankLabel}</StatusChip>
              <StatusChip tone="neutral">{row.netuidLabel}</StatusChip>
              <StatusChip tone={row.modelLabelTone}>{row.modelLabel}</StatusChip>
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{row.name}</h2>
              <p className="mt-1 text-sm text-[color:var(--text-tertiary)]">{row.updatedLabel}</p>
            </div>
          </div>

          <div className="surface-subtle p-4">
            <div className="eyebrow">Why It Ranks Here</div>
            <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
          </div>

          <div className="surface-subtle p-4">
            <div className="eyebrow">What Is Driving It</div>
            <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <TrustBadge flags={row.statusFlags} awaitingRun={row.awaitingRun} />
            </div>
            <div className="flex flex-wrap gap-2">
              {row.statusFlags.map((flag) => (
                <StatusChip key={flag.label} tone={flag.tone}>
                  {flag.label}
                </StatusChip>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="eyebrow">Trust Notes</div>
            {trustNotes(row).length ? (
              trustNotes(row).map((note) => (
                <div key={note} className="surface-subtle p-3 text-sm leading-6 text-[color:var(--text-secondary)]">
                  {note}
                </div>
              ))
            ) : (
              <div className="surface-subtle p-3 text-sm leading-6 text-[color:var(--text-secondary)]">
                No material trust warnings surfaced in the latest run.
              </div>
            )}
          </div>

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
          Hover a subnet row to inspect why it ranks here, what is driving it, and where trust is still limited.
        </div>
      )}
    </aside>
  )
}
