import Link from 'next/link'

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

          <div className="surface-subtle p-4">
            <div className="eyebrow">Why It Ranks Here</div>
            <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{row.thesisLine}</p>
          </div>

          <div className="surface-subtle p-4">
            <div className="eyebrow">What Is Driving It</div>
            <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{row.decisionLine}</p>
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
          Hover a subnet row to inspect why it ranks here and what is driving it.
        </div>
      )}
    </aside>
  )
}
