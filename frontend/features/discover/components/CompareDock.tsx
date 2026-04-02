'use client'

import Link from 'next/link'

import StatusChip from '@/components/ui/StatusChip'

interface CompareItem {
  id: number
  name: string
}

export default function CompareDock({
  items,
  onRemove,
}: {
  items: CompareItem[]
  onRemove: (id: number) => void
}) {
  if (!items.length) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 z-40 mx-auto max-w-6xl rounded-[var(--radius-xl)] border border-[color:var(--mispricing-border)] bg-[color:rgba(8,16,23,0.94)] p-4 shadow-[var(--shadow-soft)] backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="eyebrow text-[color:var(--mispricing-strong)]">Compare Dock</div>
          <p className="mt-1 text-sm text-[color:var(--text-secondary)]">
            {items.length} subnet{items.length === 1 ? '' : 's'} selected. Compare up to four side by side.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {items.map((item) => (
            <button key={item.id} type="button" onClick={() => onRemove(item.id)} className="rounded-full" aria-label={`Remove ${item.name} from compare`}>
              <StatusChip tone="mispricing">{item.name}</StatusChip>
            </button>
          ))}
          <Link href={`/compare?ids=${items.map((item) => item.id).join(',')}`} className="button-primary">
            Compare selected
          </Link>
        </div>
      </div>
    </div>
  )
}
