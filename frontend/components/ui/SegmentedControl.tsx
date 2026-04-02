'use client'

import { cn } from '@/lib/formatting'

export interface SegmentItem {
  id: string
  label: string
}

export default function SegmentedControl({
  items,
  value,
  onChange,
}: {
  items: SegmentItem[]
  value: string
  onChange: (id: string) => void
}) {
  return (
    <div className="inline-flex flex-wrap items-center gap-2 rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-2">
      {items.map((item) => {
        const active = item.id === value
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            aria-pressed={active}
            className={cn(
              'min-h-11 rounded-[var(--radius-md)] px-4 text-sm font-medium transition-all',
              active
                ? 'bg-[color:var(--surface-2)] text-[color:var(--text-primary)] shadow-[var(--shadow-soft)]'
                : 'text-[color:var(--text-secondary)] hover:bg-[color:var(--surface-2)] hover:text-[color:var(--text-primary)]',
            )}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
