import { ReactNode } from 'react'

import { SignalTone } from '@/lib/view-models/research'
import { cn } from '@/lib/formatting'

export function toneClass(tone: SignalTone): string {
  switch (tone) {
    case 'quality':
      return 'border-[color:var(--quality-border)] bg-[color:var(--quality-surface)] text-[color:var(--quality-strong)]'
    case 'mispricing':
      return 'border-[color:var(--mispricing-border)] bg-[color:var(--mispricing-surface)] text-[color:var(--mispricing-strong)]'
    case 'fragility':
      return 'border-[color:var(--fragility-border)] bg-[color:var(--fragility-surface)] text-[color:var(--fragility-strong)]'
    case 'confidence':
      return 'border-[color:var(--confidence-border)] bg-[color:var(--confidence-surface)] text-[color:var(--confidence-strong)]'
    case 'warning':
      return 'border-[color:var(--warning-border)] bg-[color:var(--warning-surface)] text-[color:var(--warning-strong)]'
    default:
      return 'border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] text-[color:var(--text-secondary)]'
  }
}

export default function StatusChip({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode
  tone?: SignalTone
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex min-h-8 items-center rounded-full border px-3 text-[11px] font-medium uppercase tracking-[0.2em]',
        toneClass(tone),
        className,
      )}
    >
      {children}
    </span>
  )
}
