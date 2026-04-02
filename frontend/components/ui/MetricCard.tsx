import { ReactNode } from 'react'

import { cn } from '@/lib/formatting'

export default function MetricCard({
  label,
  value,
  meta,
  accent,
}: {
  label: string
  value: ReactNode
  meta?: ReactNode
  accent?: 'default' | 'quality' | 'mispricing' | 'fragility' | 'confidence' | 'warning'
}) {
  return (
    <div
      className={cn(
        'surface-subtle p-4',
        accent === 'quality' && 'ring-1 ring-[color:var(--quality-border)]',
        accent === 'mispricing' && 'ring-1 ring-[color:var(--mispricing-border)]',
        accent === 'fragility' && 'ring-1 ring-[color:var(--fragility-border)]',
        accent === 'confidence' && 'ring-1 ring-[color:var(--confidence-border)]',
        accent === 'warning' && 'ring-1 ring-[color:var(--warning-border)]',
      )}
    >
      <div className="eyebrow">{label}</div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</div>
      {meta ? <div className="mt-1 text-sm text-[color:var(--text-tertiary)]">{meta}</div> : null}
    </div>
  )
}
